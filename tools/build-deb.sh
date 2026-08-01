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

cp -a "$here/debian" "$stage/$pkg-$ver/debian"

cd "$stage/$pkg-$ver"
dpkg-buildpackage -us -uc "$@"

echo
echo "built in $stage:"
ls -1 "$stage" | grep -E '\.(deb|dsc|changes|tar\.[gx]z)$' | sed 's/^/  /'
