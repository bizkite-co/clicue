import argparse
import sys

def parse_words_from_file(file_obj):
    content = file_obj.read()
    return content.split()

def main(args=None):
    parser = argparse.ArgumentParser(description="clicue - read a script and parse into words")
    parser.add_argument(
        "script",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Path to the script file (or '-' for stdin). If omitted, reads from stdin.",
    )
    
    parsed_args = parser.parse_args(args)
    
    words = parse_words_from_file(parsed_args.script)
    
    print(f"Parsed {len(words)} words.")
    return words

if __name__ == "__main__":
    main()
