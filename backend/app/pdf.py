import re
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat

STATIC_DIR = Path(__file__).parent.parent / "static"
IMAGES_DIR = STATIC_DIR / "images"


def convert_pdf_to_markdown(pdf_path: str, resource_id: int) -> tuple[str, list[str]]:
    """Convert a PDF file to markdown using docling, extracting images.

    Returns (markdown_content, list_of_image_paths).
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
    result = converter.convert(pdf_path)

    # Save extracted images
    image_dir = IMAGES_DIR / str(resource_id)
    image_dir.mkdir(parents=True, exist_ok=True)

    image_paths: list[str] = []
    for i, picture in enumerate(result.document.pictures):
        if picture.image is not None and picture.image.pil_image is not None:
            filename = f"figure_{i}.png"
            save_path = image_dir / filename
            picture.image.pil_image.save(str(save_path), format="PNG")
            image_paths.append(str(save_path))

    # Get markdown and replace image placeholders
    markdown = result.document.export_to_markdown()

    # Replace <!-- image --> placeholders with proper markdown image refs
    image_index = 0

    def replace_image_placeholder(match: re.Match[str]) -> str:
        nonlocal image_index
        if image_index < len(image_paths):
            url = f"/static/images/{resource_id}/figure_{image_index}.png"
            replacement = f"![Figure {image_index}]({url})"
            image_index += 1
            return replacement
        return match.group(0)

    markdown = re.sub(r"<!-- image -->", replace_image_placeholder, markdown)

    return markdown, image_paths
