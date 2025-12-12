#!/bin/bash

if [ -z "$1" ]; then
    echo "Error: No argument provided."
    echo "Usage: $0 [stable|nightly]"
    exit 1
fi

# Check if argument is valid
if [ "$1" != "stable" ] && [ "$1" != "nightly" ]; then
    echo "Error: Invalid argument '$1'. Must be 'stable' or 'nightly'."
    exit 1
fi


GITHUB_USER="crocs-muni"

# Add github access token
GITHUB_TOKEN=""

# Add directory where the repo will be cloned to
BASE_DIR=""
REPO_NAME="coinjoin"
BRANCH="main" 

cd $BASE_DIR

if [ ! -d "$REPO_NAME" ]; then
  echo "Cloning repository..."
git clone https://$GITHUB_USER:$GITHUB_TOKEN@github.com/$GITHUB_USER/$REPO_NAME.git

  if [ $? -ne 0 ]; then
    echo "Error cloning repository."
    exit 1
  fi
fi

cd $REPO_NAME || exit
git checkout main
git fetch
git pull --force

if [ "$1" == "nightly" ]; then
echo "running nightly build..."
python ./python_scripts/build.py
echo "nightly build done"
else 
cd ./stable
echo "running stable build..."
python ./python_scripts/build.py
echo "stable build done"
cd ..
fi

git config user.name "bot"
git config user.email "bot@bot.bot"
git add -A

if ! git diff --quiet || ! git diff --cached --quiet; then
  git commit -m "Update figures"
  git push origin $BRANCH
else
  echo "No changes to commit."
fi