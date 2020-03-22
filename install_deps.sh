#!/bin/bash

# Installs dependencies for Glader where possible/needed.
# -Christopher Welborn 03-17-2020
appname="Glader Dependency Installer"
appversion="0.0.1"
apppath="$(readlink -f "${BASH_SOURCE[0]}")"
appscript="${apppath##*/}"
#appdir="${apppath%/*}"

# Packages that Glader depends on.
declare -a apt_deps=(
    "gir1.2-gtk-3.0"
    "libgtksourceview-3.0-dev"
    "python3-gi"
)

if hash apt &>/dev/null; then
    apt_exe="apt"
elif hash apt-get &>/dev/null; then
    apt_exe="apt-get"
else
    printf "\nMissing \`apt\`/\`apt-get\` commands, cannot install dependencies.\n" 1>&2
    printf "You will need packages like these:\n" 1>&2
    printf "    %s\n" "${apt_deps[@]}"
    exit 1
fi
declare -a cmd_deps=("dpkg" "awk")
for cmd_dep in "${cmd_deps[@]}"; do
    hash "$cmd_dep" &>/dev/null || {
        printf "\nMissing \`%s\` command, cannot install dependencies.\n" "$cmd_dep" 1>&2
        printf "You will need packages like these:\n" 1>&2
        printf "    %s\n" "${apt_deps[@]}"
        exit 1
    }
done


function do_apt {
    declare -a need_deps
    local try_dep
    for try_dep in "${apt_deps[@]}"; do
        is_apt_installed "$try_dep" || need_deps+=("$try_dep")
    done


    if ((${#need_deps[@]})); then
        printf "\nTrying to install missing apt packages:\n"
        printf "    %s\n" "${need_deps[@]}"
        install_apt "${need_deps[@]}"
    else
        printf "\nAll apt dependencies are installed.\n\n"
    fi
}

function do_pip {
    declare -a pip_deps
    mapfile -t pip_deps < <(get_pip_deps)
    ((${#pip_deps[@]})) || fail "Missing pip dependencies."
    declare -a need_deps
    local try_dep
    for try_dep in "${pip_deps[@]}"; do
        is_pip_installed "$try_dep" || need_deps+=("$try_dep")
    done

    if ((${#need_deps[@]})); then
        printf "\nTrying to install missing pip packages:\n"
        printf "    %s\n" "${need_deps[@]}"
        install_pip "${need_deps[@]}"
    else
        printf "\nAll pip dependencies are installed.\n\n"
    fi
}
function echo_err {
    # Echo to stderr.
    echo -e "$@" 1>&2
}

function fail {
    # Print a message to stderr and exit with an error status code.
    echo_err "$@"
    exit 1
}

function fail_usage {
    # Print a usage failure message, and exit with an error status code.
    print_usage "$@"
    exit 1
}

function get_pip_deps {
    awk -F '[ >=<!]' '{print $1}' requirements.txt
}

function get_python3 {
    declare -a try_exes=(
        "python4"
        "python3.9"
        "python3.8"
        "python3.7"
        "python3.6"
        "python3"
        "python"
    )
    local try_exe
    for try_exe in "${try_exes[@]}"; do
        hash "$try_exe" &>/dev/null && {
            printf "%s" "$try_exe"
            return 0
        }
    done
    [[ -n "$USE_PY" ]] && {
        printf "%s" "$USE_PY"
        return 0
    }
    return 1
}

function install_apt {
    sudo "$apt_exe" install "$@"
}

function install_pip {
    "$python3_exe" -m pip install --user "$@"
}

function is_apt_installed {
    # Return 0 if an apt package is installed, otherwise 1.
    printf "Looking for apt package: %s\n" "$1"
    dpkg -s "$1" &>/dev/null
}

function is_pip_installed {
    printf "Looking for pip package: %s\n" "$1"
    "$python3_exe" -m pip show "$1" &>/dev/null
}

function print_usage {
    # Show usage reason if first arg is available.
    [[ -n "$1" ]] && echo_err "\n$1\n"

    echo "$appname v. $appversion

    Usage:
        $appscript -h | -v

    Options:
        -h,--help     : Show this message.
        -v,--version  : Show $appname version and exit.
    "
}

declare -a nonflags

for arg; do
    case "$arg" in
        "-h" | "--help")
            print_usage ""
            exit 0
            ;;
        "-v" | "--version")
            echo -e "$appname v. $appversion\n"
            exit 0
            ;;
        -*)
            fail_usage "Unknown flag argument: $arg"
            ;;
        *)
            nonflags+=("$arg")
    esac
done

do_apt

if ! python3_exe="$(get_python3)"; then
    fail "Unable to determine python 3+ executable. Set \$USE_PY before running this."
fi
do_pip
