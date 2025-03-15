#!/usr/bin/env python3
"""
Typst Mermaid Diagram Processor

This script processes Mermaid diagrams in Typst files, converting them to images
and updating the document references accordingly.

Requirements:
    - Python 3.6+
    - Mermaid CLI (@mermaid-js/mermaid-cli)

Usage:
    python process_diagrams.py [file_path]
    If no file_path is provided, you can navigate through the filesystem.
"""

import re
import os
import sys
import subprocess
from hashlib import sha1
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager

class Config:
    """Configuration settings for the script."""

    IMAGE_FORMAT = "png"
    MERMAID_CLI = "mmdc"
    DEFAULT_BACKGROUND = "transparent"

@contextmanager
def change_working_directory(path: Path):
    """Change the working directory to the specified path."""
    original_dir = Path.cwd()
    try:
        os.chdir(str(path))
        yield
    finally:
        os.chdir(str(original_dir))

class MermaidProcessor:
    """Processes Mermaid diagrams in Typst files."""

    def __init__(self, file_path: Path):
        """Initialize the processor with a file path."""
        self.file_path = file_path
        self.content: str = ""
        self.diagrams: List[str] = []

    def _check_mermaid_cli(self) -> bool:
        """Check if Mermaid CLI is installed."""
        try:
            proc = subprocess.run(
                [Config.MERMAID_CLI, "--version"],
                capture_output=True,
                check=True,
                shell=True,
            )
            print(proc.stdout.decode())
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _read_file(self) -> bool:
        """Read the content of the input file."""
        try:
            self.content = self.file_path.read_text(encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return False

    def extract_diagrams(self) -> List[str]:
        """Extract Mermaid diagrams from the content."""
        self.diagrams = re.findall(r"```mermaid\n([\s\S]*?)\n```", self.content)
        return self.diagrams

    def extract_metadata(self, diagram: str) -> Dict[str, str]:
        """Extract metadata from diagram comments."""
        metadata = {}
        lines = diagram.split("\n")
        for line in lines:
            if line.startswith("%%"):
                key, *value = line[2:].split(":")
                metadata[key.strip()] = ":".join(value).strip()
        return metadata

    def render_diagram(self, diagram: str) -> Tuple[bool, str]:
        """Render a single diagram to an image file only if needed else return true."""
        try:
            code = "\n".join([line for line in diagram.split("\n") if (not line.startswith("%%")) and len(line.strip()) > 0])
            hashcode = sha1(code.encode()).hexdigest()
            output_path = f"{hashcode}.{Config.IMAGE_FORMAT}"

            if Path(output_path).exists():
                print(f"Diagram already rendered: {output_path}")
                return True, output_path
            
            cmd = [
                Config.MERMAID_CLI,
                "-i",
                "-",
                "-b",
                Config.DEFAULT_BACKGROUND,
                "-o",
                output_path,
            ]

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
            )

            stdout, stderr = process.communicate(input=diagram)

            if process.returncode != 0:
                raise subprocess.SubprocessError(f"Mermaid CLI error: {stderr}")

            return True, output_path

        except Exception as e:
            return False, str(e)

    def process_content(self) -> str:
        """Process the content and replace diagrams with image references."""
        processed_content = self.content

        for diagram in self.diagrams:
            #Encode only the diagram code, not any extra arguments or the caption
            diagram_code = "\n".join([line for line in diagram.split("\n") if (not line.startswith("%%")) and len(line.strip()) > 0])
            hashcode = sha1(diagram_code.encode()).hexdigest()
            
            caption = ""
            args = ""
            
            for line in diagram.split("\n"):
                if line.startswith("%%!"):
                    caption = line[3:].strip()
                elif line.startswith("%%"):
                    args = line[2:].strip()
                else:
                    break

            image_ref = f'#figure(image("./{hashcode}.{Config.IMAGE_FORMAT}", {args}), caption: "{caption}")'
            processed_content = processed_content.replace(
                f"```mermaid\n{diagram}\n```", image_ref, 1
            )

        return processed_content

    def save_output(self, content: str) -> bool:
        """Save the processed content to a file."""
        try:
            stem = self.file_path.stem
            output_path = self.file_path.parent / f"{stem}.rendered.typ"
            output_path.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return False

    def process(self) -> bool:
        """Main processing function."""
        if not self._check_mermaid_cli():
            print(
                "Error: Mermaid CLI not found. Please install @mermaid-js/mermaid-cli"
            )
            return False

        if not self._read_file():
            return False

        self.extract_diagrams()

        if not self.diagrams:
            print("No Mermaid diagrams found in the file")
            return False

        with change_working_directory(self.file_path.parent):
            for diagram in self.diagrams:
                success, result = self.render_diagram(diagram)
                if not success:
                    print(f"Error rendering diagram: {result}")
                    return False

            processed_content = self.process_content()

            if self.save_output(processed_content):
                print("Processing completed successfully")
                return True
    
        return False


def list_directory(path: Path = Path(".")) -> List[Path]:
    """List contents of the current directory."""
    try:
        items = sorted(path.iterdir())
        # Filter out non-Typst files, but keep directories
        items = [
            item
            for item in items
            if item.is_dir() or item.suffix in [".typ", ".mtyp"]
        ]
        return items
    except Exception as e:
        print(f"Error listing directory: {str(e)}")
        return []


def navigate_filesystem() -> Optional[Path]:
    """Interactive filesystem navigation."""
    current_path = Path(__file__).parent.absolute()

    while True:
        print(f"\nCurrent directory: {current_path}")
        print("\nDirectory contents:")
        items = list_directory(current_path)

        for idx, item in enumerate(items, 1):
            item_type = "D" if item.is_dir() else "F"
            print(f"{idx}. [{item_type}] {item.name}")

        print("\nOptions:")
        print("number. Select item by number")
        print("p. Go to parent directory")
        print("q. Quit")

        choice = input("\nEnter your choice: ").lower().strip()

        if choice == "q":
            return None
        elif choice == "p":
            parent = current_path.parent
            if parent != current_path:
                current_path = parent
            continue
        else:
            # Try to interpret the input as a number directly
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    selected = items[idx]

                    if selected.is_dir():
                        current_path = selected
                        continue
                    elif selected.suffix in [".typ", ".mtyp"]:
                        return selected
                    else:
                        print(
                            "Selected file is not a Typst file (.typ) or mermaid-enabled Typst file (.mtyp)"
                        )
                else:
                    print("Invalid item number")
            except ValueError:
                print("Invalid choice - enter a number, 'p' for parent, or 'q' to quit")


def resolve_path(path_str: str) -> Path:
    """
    Resolve a path to its absolute path, handling relative paths.
    Supports:
    - Absolute paths
    - Relative paths from current directory (./path or path)
    - Relative paths from parent directories (../path)
    - Home directory paths (~/)
    """
    path = Path(path_str)
    
    # Expand user directory (~/...)
    if str(path).startswith("~"):
        path = Path(path.expanduser())

    # If it's already absolute, just normalize it
    if path.is_absolute():
        return path

    # Handle relative paths
    # Get the current working directory (where the script is run from)
    cwd = Path.cwd()

    # Combine and normalize the path
    full_path = (cwd / path).resolve()

    return full_path


def validate_file_path(path: Path) -> Tuple[bool, str]:
    """
    Validate a file path and return whether it's valid and an error message if not.
    """
    if not path.exists():
        return False, f"File not found: {path}"

    if not path.is_file():
        return False, f"Not a file: {path}"

    if path.suffix != ".typ":
        return False, f"Not a Typst file: {path}"

    return True, ""


def main():
    """Main entry point of the script."""
    # Get file path from command line or through navigation
    if len(sys.argv) > 1:
        # Resolve the provided path
        file_path = resolve_path(sys.argv[1])

        # Validate the path
        is_valid, error_msg = validate_file_path(file_path)
        if not is_valid:
            print(f"Error: {error_msg}")
            print("Usage: python process_diagrams.py [path/to/file.typ]")
            print("Examples:")
            print("  python process_diagrams.py ./document.typ")
            print("  python process_diagrams.py ~/documents/file.typ")
            print("  python process_diagrams.py ../other/file.typ")
            sys.exit(1)
    else:
        file_path = navigate_filesystem()

    if not file_path:
        print("No file selected. Exiting...")
        sys.exit(1)

    processor = MermaidProcessor(file_path)
    if not processor.process():
        sys.exit(1)


if __name__ == "__main__":
    main()