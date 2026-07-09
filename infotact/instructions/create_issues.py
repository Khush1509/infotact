import re
import urllib.request
import urllib.error
import json
import argparse
import sys
import os
import io

# Fix Windows Unicode encoding issues
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def parse_issues_markdown(filepath):
    """
    Parses docs/github_issues.md and returns a list of dictionaries,
    each containing title, body, and labels.
    """
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        sys.exit(1)
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the markdown heading "## Issue "
    blocks = content.split("## Issue ")
    issues = []
    
    for block in blocks[1:]:  # Skip the first element which is the header
        lines = block.split('\n')
        if not lines:
            continue
            
        # Parse Title (first line)
        title_line = lines[0].strip()
        # Remove prefix like "1: " or "13: "
        title_match = re.match(r'^\d+:\s*(.*)$', title_line)
        if title_match:
            title = title_match.group(1)
        else:
            title = title_line
            
        # Parse Labels and Body
        labels = []
        body_lines = []
        found_labels = False
        
        for line in lines[1:]:
            stripped_line = line.strip()
            if not found_labels and stripped_line.startswith("**Labels**:") or stripped_line.startswith("Labels:"):
                # Extract words inside backticks or just general words
                labels_part = re.sub(r'^\*\*Labels\*\*:\s*', '', stripped_line)
                labels_part = re.sub(r'^Labels:\s*', '', labels_part)
                # Split by comma and clean backticks
                for lbl in labels_part.split(','):
                    lbl_clean = lbl.replace('`', '').strip()
                    if lbl_clean:
                        labels.append(lbl_clean)
                found_labels = True
            else:
                body_lines.append(line)
                
        body = '\n'.join(body_lines).strip()
        issues.append({
            "title": title,
            "body": body,
            "labels": labels
        })
        
    return issues

def create_github_issue(token, repo, issue):
    """
    Calls the GitHub API to create an issue.
    """
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Infotact-Issues-Creator-Agent"
    }
    
    data = json.dumps({
        "title": issue["title"],
        "body": issue["body"],
        "labels": issue["labels"]
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"[OK] Created issue #{res_data.get('number')}: '{issue['title']}'")
            return res_data.get('html_url')
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode('utf-8')
        print(f"[FAIL] Failed to create issue '{issue['title']}': HTTP {e.code} - {e.reason}")
        print(f"Details: {error_msg}")
        return None
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Automate creation of 16 GitHub Issues for Infotact Project")
    parser.add_argument("--token", help="GitHub Personal Access Token (PAT) with repo scope", required=False)
    parser.add_argument("--repo", help="Target GitHub Repo in format 'owner/repo'", default="Khush1509/infotact")
    parser.add_argument("--dry-run", help="Parse and print the issues without publishing", action="store_true")
    
    args = parser.parse_args()
    
    # Path to the issues markdown
    base_dir = os.path.dirname(os.path.abspath(__file__))
    issues_path = os.path.join(base_dir, 'github_issues.md')
    
    print("Parsing issues from:", issues_path)
    issues = parse_issues_markdown(issues_path)
    print(f"Successfully parsed {len(issues)} issues.\n")
    
    if args.dry_run:
        print("=== DRY RUN MODE ===")
        for i, issue in enumerate(issues, 1):
            print(f"Issue #{i}:")
            print(f"  Title : {issue['title']}")
            print(f"  Labels: {', '.join(issue['labels'])}")
            print(f"  Body Length: {len(issue['body'])} chars")
            print("-" * 40)
        sys.exit(0)
        
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: Personal Access Token is required to call GitHub API.")
        print("Please provide it via --token argument or set the GITHUB_TOKEN environment variable.")
        print("\nTo do a dry run check, run:")
        print("  python scripts/create_issues.py --dry-run")
        sys.exit(1)
        
    print(f"Starting creation of {len(issues)} issues in repository '{args.repo}'...")
    successful_count = 0
    for issue in issues:
        url = create_github_issue(token, args.repo, issue)
        if url:
            successful_count += 1
            
    print(f"\nDone! Created {successful_count}/{len(issues)} issues successfully.")

if __name__ == "__main__":
    main()
