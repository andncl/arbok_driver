#!/usr/bin/env bash

pushd `git rev-parse --show-toplevel`/.git/hooks
ln -s ../../tools/github.hooks/linux/pre-commit
popd