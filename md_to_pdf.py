#!/usr/bin/env python3
"""
Markdown to PDF converter for research papers.
Uses markdown + weasyprint for high-quality PDF output.
"""

import markdown
from weasyprint import HTML, CSS
from pathlib import Path

# CSS styling for academic paper look
PAPER_CSS = """
@page {
    size: letter;
    margin: 1in;
    @bottom-center {
        content: counter(page);
        font-size: 10pt;
        color: #666;
    }
}

body {
    font-family: "Times New Roman", Times, Georgia, serif;
    font-size: 12pt;
    line-height: 1.6;
    color: #333;
    max-width: 100%;
}

h1 {
    font-size: 18pt;
    font-weight: bold;
    text-align: center;
    margin-top: 0;
    margin-bottom: 0.5em;
    color: #000;
}

h2 {
    font-size: 14pt;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    color: #000;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.2em;
}

h3 {
    font-size: 12pt;
    font-weight: bold;
    margin-top: 1em;
    margin-bottom: 0.5em;
    color: #333;
}

p {
    margin-bottom: 0.8em;
    text-align: justify;
}

ul, ol {
    margin-bottom: 1em;
    padding-left: 2em;
}

li {
    margin-bottom: 0.3em;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 11pt;
}

th, td {
    border: 1px solid #999;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f0f0f0;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 1.5em 0;
}

code {
    font-family: "Courier New", Courier, monospace;
    font-size: 10pt;
    background-color: #f4f4f4;
    padding: 0.1em 0.3em;
    border-radius: 3px;
}

pre {
    background-color: #f4f4f4;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    font-size: 10pt;
}

blockquote {
    border-left: 3px solid #ccc;
    padding-left: 1em;
    margin-left: 0;
    font-style: italic;
    color: #555;
}

strong {
    font-weight: bold;
}

em {
    font-style: italic;
}
"""


def convert_md_to_pdf(input_path: str, output_path: str = None) -> str:
    """
    Convert a markdown file to PDF.

    Args:
        input_path: Path to the input markdown file
        output_path: Path for the output PDF (optional, defaults to same name with .pdf)

    Returns:
        Path to the generated PDF file
    """
    input_file = Path(input_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_path is None:
        output_path = input_file.with_suffix('.pdf')
    else:
        output_path = Path(output_path)

    # Read markdown content
    md_content = input_file.read_text(encoding='utf-8')

    # Convert markdown to HTML with extensions for tables
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'toc']
    )

    # Wrap in full HTML document
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{input_file.stem}</title>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Convert to PDF
    html = HTML(string=full_html)
    css = CSS(string=PAPER_CSS)
    html.write_pdf(str(output_path), stylesheets=[css])

    return str(output_path)


def main():
    """Main entry point."""
    import sys

    # Default to Plan.md if no argument provided
    if len(sys.argv) < 2:
        input_file = Path(__file__).parent / "Plan.md"
    else:
        input_file = Path(sys.argv[1])

    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Converting {input_file} to PDF...")
    result = convert_md_to_pdf(str(input_file), output_file)
    print(f"PDF generated: {result}")


if __name__ == "__main__":
    main()
