#!/bin/sh
# Build the Debian package out of tree.
#
# dpkg-buildpackage wants a source directory named <package>-<version> and an
# .orig tarball beside it, neither of which the working tree is. Rather than
# rename the working tree, everything is copied to a staging directory and
# built there, so a build never touches the tree you are editing.
#
# The orig tarball deliberately excludes fortune/. Those files are build
# products of tools/make_fortune.py, debian/rules regenerates them, and
# debian/rules clean removes them again -- and `3.0 (quilt)` cannot represent
# the deletion of a file that came out of the orig tarball.

set -eu

here=$(cd "$(dirname "$0")/.." && pwd)
pkg=hadith
ver=$(dpkg-parsechangelog -l "$here/debian/changelog" -S Version | sed 's/-[^-]*$//')
stage=${1:-${TMPDIR:-/tmp}/hadith-build}
if [ $# -gt 0 ]; then shift; fi # the rest goes to dpkg-buildpackage

rm -rf "$stage"
mkdir -p "$stage/$pkg-$ver"

# Everything not gitignored, not an editor's, and not a build product.
tar -C "$here" -cf - \
	--exclude=./debian \
	--exclude=./fortune \
	--exclude=./corpus/raw \
	--exclude=./reference \
	--exclude=./pilot/data \
	--exclude='./pilot/out*' \
	--exclude=./.git \
	--exclude=./.idea \
	--exclude='*/__pycache__' \
	--exclude='*.pyc' \
	. | tar -C "$stage/$pkg-$ver" -xf -

# Reproducible tarball: sorted names, no owner or timestamp variation.
tar -C "$stage" \
	--sort=name \
	--mtime="@$(dpkg-parsechangelog -l "$here/debian/changelog" -S Timestamp)" \
	--owner=0 --group=0 --numeric-owner \
	-czf "$stage/${pkg}_${ver}.orig.tar.gz" "$pkg-$ver"

# The upstream signature.
#
# debian/upstream/signing-key.asc is part of the packaging, and lintian then
# requires an .asc beside the orig tarball -- W: orig-tarball-missing-upstream-
# signature otherwise. dpkg-source picks the file up on its own and lists it in
# the .dsc, so signing it here is all that is needed.
#
# Off by default, because a plain local build should not touch the key and
# because CI has no key to touch. SIGNED_SOURCE=1 turns it on, since a mentors
# upload does have to carry the signature.
#
# The key is selected by the address in debian/changelog, the same rule
# dpkg-buildpackage uses, so there is one place that decides which key signs.
if [ "${SIGN_ORIG:-${SIGNED_SOURCE:-0}}" = "1" ]; then
	signer=$(dpkg-parsechangelog -l "$here/debian/changelog" -S Maintainer |
		sed 's/.*<\(.*\)>.*/\1/')
	echo "signing ${pkg}_${ver}.orig.tar.gz as $signer"
	gpg --armor --detach-sign --local-user "$signer" \
		--output "$stage/${pkg}_${ver}.orig.tar.gz.asc" \
		"$stage/${pkg}_${ver}.orig.tar.gz"
fi

cp -a "$here/debian" "$stage/$pkg-$ver/debian"

cd "$stage/$pkg-$ver"

# Unsigned and full by default, which is what a local check wants.
#
# SIGNED_SOURCE=1 instead builds a source-only package and signs it, which is
# what mentors.debian.net requires -- its dput target sets
# allow_unsigned_uploads = 0, and it wants the source, not our binaries.
# dpkg-buildpackage picks the key by the address in debian/changelog, so that
# address and the key's uid have to agree.
if [ "${SIGNED_SOURCE:-0}" = "1" ]; then
	dpkg-buildpackage -S -sa "$@"
else
	dpkg-buildpackage -us -uc "$@"
fi

echo
echo "built in $stage:"
ls -1 "$stage" | grep -E '\.(deb|dsc|changes|tar\.[gx]z|asc)$' | sed 's/^/  /'
