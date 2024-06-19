#!/usr/bin/env bash
#de-identify notebooks of home path
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
echo $SCRIPT_DIR
nbPath=$SCRIPT_DIR/..
nbs=$nbPath/*.ipynb
for f in $nbs; do
  sed -i "s|$HOME|~|g" $f
done