#!/bin/bash

function error() {
	echo "ERROR: $1"
	exit 1
}

# Required binaries/apps
reqs=('pytest' 'coverage')
for req in ${reqs[*]}; do
	[[ -z "$(command -v $req)" ]] && error "$req not found"
done
# Check for pytest-cov module
python -c "import pytest_cov" 2>/dev/null || error "pytest-cov module not found"

python -m pytest --cov=networkd_dispatcher -q tests
