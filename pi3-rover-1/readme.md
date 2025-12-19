After Installed Ubuntu Server 24.04.3 LTS (64-Bits) with Raspberry Pi Imager

Ssh to the pi3-rover-1.local and 
- sudo apt update
- sudo apt install -y python3-venv python3-pip
- install the requirements.txt

For the development workflow, i will have a monorepo and portion of the code is need to push to the pi for testing, plan is to use git subtree to push a subfolder to the Pi.

On the Pi, set up a bare “deploy” repo (once):
# on Pi
sudo apt install -y git

mkdir -p /home/sunnyday/deploy
cd /home/sunnyday/deploy
git init --bare pi3-rover-1.git # pi3-rover-1 is the folder name in the repo

Create a working tree where code will be checked out:
mkdir -p /home/sunnyday/apps/pi3-rover-1

Add the server-side hook:
    cat > /home/sunnyday/deploy/pi3-rover-1.git/hooks/post-receive <<'EOF'
    #!/usr/bin/env bash
    set -euo pipefail

    LOG=/home/sunnyday/deploy/pi3-rover-1-deploy.log
    exec >>"$LOG" 2>&1

    WORKTREE=/home/sunnyday/apps/pi3-rover-1
    GIT_DIR=/home/sunnyday/deploy/pi3-rover-1.git

    mkdir -p "$WORKTREE"

    # Read what was pushed; deploy only when main is updated
    while read -r old new ref; do
    if [[ "$ref" == "refs/heads/main" ]]; then
        git --work-tree="$WORKTREE" --git-dir="$GIT_DIR" checkout -f main
    fi
    done
    EOF

    chmod +x /home/sunnyday/deploy/pi3-rover-1.git/hooks/post-receive


# On Mac, add the Pi remote:
git remote add pi sunnyday@pi3-rover-1.local:/home/sunnyday/deploy/pi3-rover-1.git

Push only the subfolder pi3-rover-1/:
git subtree push --prefix pi3-rover-1 pi main


# prep and get dashboard ready
cd ~/apps/pi3-rover-1/dashboard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# To run dashbaord
cd ~/apps/pi3-rover-1/dashboard
source .venv/bin/activate
python -m backend.main