# Custom shell prompt for zeus-dev-image, sourced from /etc/profile.d/.
# Shows user@host, the current directory, and the git branch when inside a
# repo. Not executable on its own -- it is meant to be sourced.
zeus_git_branch() {
    branch=$(git symbolic-ref --short HEAD 2>/dev/null) || return 0
    printf ' (%s)' "$branch"
}

PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]$(zeus_git_branch)\$ '
export PS1
