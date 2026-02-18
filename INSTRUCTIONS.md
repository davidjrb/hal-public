# Instructions for Next LLM

This document outlines how to seamlessly connect to the server and utilize the Git repository.

## SSH Access

- **User**: `<YOUR_USER>`
- **Host**: `<YOUR_SERVER_IP>`
- **Command**: `ssh <YOUR_USER>@<YOUR_SERVER_IP>`
- **Authentication**: Public Key Authentication (Ensure your local SSH key is configured).

## Git Repository

- **Location**: `~/instructions`
- **Remote**: `<YOUR_REPO_URL>`
- **Branch**: `main`

### Workflow

The server is pre-configured with a deploy key for GitHub access. You can run Git commands directly from the repository directory.

1.  **Navigate to the Repo**:
    ```bash
    cd ~/instructions
    ```

2.  **Pull Updates**:
    ```bash
    git pull origin main
    ```

3.  **Make Changes**:
    Edit files using `nano`, `vim`, or echo commands.

4.  **Confirm Changes**:
    Always run `git status` and `git diff` before committing.

5.  **Commit and Push**:
    ```bash
    git add .
    git commit -m "Your commit message"
    git push origin main
    ```

## Notes

- Git user name is configured as `HAL 9000`.
- Git email is configured as `<YOUR_USER>@<YOUR_SERVER_IP>`.
- The SSH config at `~/.ssh/config` handles the identity file for GitHub.
