import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="clicue - read a script and parse into words")
    parser.add_argument(
        "script",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Path to the script file (or '-' for stdin). If omitted, reads from stdin.",
    )
    
    args = parser.parse_args()
    
    # Read the content
    content = args.script.read()
    
    # Parse the script into a list of words
    words = content.split()
    
    print(f"Parsed {len(words)} words.")

if __name__ == "__main__":
    main()
