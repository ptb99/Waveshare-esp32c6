#! /bin/sh

###
### Make a bitmap font from a TT/etc scalable font (for use w/ CircuitPython)
###

Usage() {
    echo "usage: mkfont.sh FONTFILE SIZE"
    echo "    ex: /usr/share/fonts/gnu-free/FreeSans.ttf 24"
    exit 2
}


SRC=$1
SIZE=$2
ext=${SRC##*.}
OUT=$(basename ${SRC} .${ext})-${SIZE}.pcf

[ -f ${SRC} ] || Usage
[ ${SIZE} -gt 0 ] || Usage

# (greatly) reduce file size by limiting the encoding
OPTS="-r 72 -m iso8859.1"
## grab encoding map file from:
## https://github.com/jirutka/otf2bdf/blob/master/maps/iso8859.1

echo "otf2bdf -p ${SIZE} ${OPTS} ${SRC} | bdftopcf > ${OUT}"
otf2bdf -p ${SIZE} ${OPTS} ${SRC} | bdftopcf -o ${OUT}


# Good fonts (use ftstring):
#/usr/share/fonts/urw-base35/NimbusSansNarrow-Regular.otf
#/usr/share/fonts/google-noto/NotoSans-CondensedMedium.ttf
#/usr/share/fonts/gnu-free/FreeSans.ttf
