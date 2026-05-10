import zipfile
import os
import logging
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from lxml import etree
from data import NAMESPACES
from ._file_service import FileService

logger = logging.getLogger(__name__)

class BookError(Exception):
    """Base exception for book service errors."""

class EpubStructureError(BookError):
    """Raised when the EPUB file structure is invalid."""

class MetadataUpdateError(BookError):
    """Raised when metadata update fails."""

class NetworkError(BookError):
    """Raised when an external service is unavailable or a network error occurs."""

class BookService:
    """Service for handling EPUB-specific business logic."""
    
    def find_books(self, directory: Union[str, Path], recursive: bool = True) -> List[Path]:
        """Finds EPUB files in the given directory."""
        return FileService.find_files(directory, "*.epub", recursive)

    def get_metadata(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Extract basic metadata from an EPUB file efficiently."""
        path = Path(path)
        metadata = {'title': 'Unknown Title', 'author': 'Unknown Author', 'publisher': '', 'date': '', 'isbn': '', 'path': str(path)}
        try:
            with zipfile.ZipFile(path, 'r') as zin:
                rootfile_path, opf_tree = self._get_opf_info(zin)

                title_elem = opf_tree.find('.//dc:title', namespaces=NAMESPACES)
                author_elem = opf_tree.find('.//dc:creator', namespaces=NAMESPACES)
                publisher_elem = opf_tree.find('.//dc:publisher', namespaces=NAMESPACES)
                date_elem = opf_tree.find('.//dc:date', namespaces=NAMESPACES)
                identifier_elems = opf_tree.xpath('.//dc:identifier/text()', namespaces=NAMESPACES)
                
                metadata['title'] = self._get_text_or_default(title_elem, 'Unknown Title')
                metadata['author'] = self._get_text_or_default(author_elem, 'Unknown Author')
                metadata['publisher'] = self._get_text_or_default(publisher_elem, '')
                metadata['date'] = self._get_text_or_default(date_elem, '')
                metadata['isbn'] = self._extract_isbn(identifier_elems)
                
        except Exception as e:
            logger.error(f"Failed to read metadata from {path}: {e}")
        return metadata

    def _get_text_or_default(self, element: Optional[etree._Element], default: str) -> str:
        """Safely extracts text from an XML element or returns a default."""
        if element is not None and element.text:
            return element.text.strip()
        return default

    def _extract_isbn(self, identifiers: List[str]) -> str:
        """Attempts to find a 10 or 13 digit ISBN from identifier strings."""
        for entry in identifiers:
            # Remove non-digits
            clean = "".join(filter(str.isdigit, entry))
            if len(clean) in (10, 13):
                return clean
        return ""

    def format_filename(self, template: str, metadata: Dict[str, Any]) -> str:
        """Generates a sanitized filename based on a template and metadata."""
        date_val = metadata.get('date') or ""
        year = date_val[:4] if date_val[:4].isdigit() else "Unknown"
        
        try:
            name = template.format(
                year=year,
                title=metadata.get('title') or "Unknown",
                author=metadata.get('author') or "Unknown",
                publisher=metadata.get('publisher') or "Unknown",
                date=metadata.get('date') or "Unknown"
            )
            if not name.lower().endswith(".epub"):
                name += ".epub"
            # Sanitize path separators
            return name.replace("/", "_").replace("\\", "_")
        except Exception as e:
            logger.error(f"Error formatting filename with template '{template}': {e}")
            return ""

    def _get_opf_info(self, zin: zipfile.ZipFile):
        """Helper to find rootfile path and parse OPF tree."""
        with zin.open('META-INF/container.xml') as container_file:
            tree = etree.parse(container_file)
            nodes = tree.xpath('//n:rootfile/@full-path', namespaces=NAMESPACES)
            if not nodes:
                raise EpubStructureError("No rootfile path found in container.xml")
            rootfile_path = nodes[0].lstrip('/')

        with zin.open(rootfile_path) as opf_file:
            opf_tree = etree.parse(opf_file)
        
        return rootfile_path, opf_tree

    def update_metadata(self, path: Union[str, Path], new_metadata: Dict[str, Any]):
        """Update EPUB metadata non-destructively."""
        def update_logic(opf_tree, _):
            if 'title' in new_metadata:
                self._set_opf_tag(opf_tree, 'title', new_metadata['title'])
            if 'author' in new_metadata:
                self._set_opf_tag(opf_tree, 'creator', new_metadata['author'])
            if 'publisher' in new_metadata:
                self._set_opf_tag(opf_tree, 'publisher', new_metadata['publisher'])
            if 'date' in new_metadata:
                self._set_opf_tag(opf_tree, 'date', new_metadata['date'])
            if 'isbn' in new_metadata:
                self._set_identifier_tag(opf_tree, new_metadata['isbn'])
            return opf_tree, None

        self._update_epub_zip(path, update_logic)

    def _update_epub_zip(self, path: Union[str, Path], process_func):
        """Internal helper to handle the common logic of updating an EPUB archive."""
        path = Path(path)
        temp_path = str(path) + ".tmp"
        try:
            with zipfile.ZipFile(path, 'r') as zin:
                rootfile_path, opf_tree = self._get_opf_info(zin)
                with zipfile.ZipFile(temp_path, 'w') as zout:
                    if 'mimetype' in zin.namelist():
                        zout.writestr('mimetype', zin.read('mimetype'), compress_type=zipfile.ZIP_STORED)
                    
                    new_opf_tree, internal_img_update = process_func(opf_tree, rootfile_path)

                    for item in zin.infolist():
                        if item.filename == 'mimetype': 
                            continue
                        if item.filename == rootfile_path:
                            zout.writestr(item.filename, etree.tostring(new_opf_tree, encoding='utf-8', xml_declaration=True), compress_type=zipfile.ZIP_DEFLATED)
                        elif internal_img_update and item.filename == internal_img_update['path']:
                            if internal_img_update['new_data'] is not None:
                                zout.writestr(item.filename, internal_img_update['new_data'], compress_type=zipfile.ZIP_DEFLATED)
                            # If new_data is None, we skip writing it (effectively deleting it)
                        else:
                            zout.writestr(item, zin.read(item.filename))
            os.replace(temp_path, path)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            logger.error(f"ZIP update failed for {path}: {e}")
            raise MetadataUpdateError(str(e))

    def _set_opf_tag(self, opf_tree, tag_name: str, value: str):
        """Helper to update or create a dc: tag in the OPF metadata."""
        elem = opf_tree.find(f'.//dc:{tag_name}', namespaces=NAMESPACES)
        if elem is not None:
            elem.text = value
        else:
            metadata_tag = opf_tree.find('.//opf:metadata', namespaces=NAMESPACES)
            if metadata_tag is not None:
                new_elem = etree.SubElement(metadata_tag, f"{{{NAMESPACES['dc']}}}{tag_name}")
                new_elem.text = value

    def _set_identifier_tag(self, opf_tree, isbn: str):
        """Updates or adds an ISBN identifier."""
        if not isbn: return
        # Try to find an existing ISBN identifier
        found = False
        ids = opf_tree.xpath('.//dc:identifier', namespaces=NAMESPACES)
        for node in ids:
            if node.text and ("isbn" in node.text.lower() or len("".join(filter(str.isdigit, node.text))) in (10, 13)):
                node.text = f"urn:isbn:{isbn}"
                found = True
                break
        
        if not found:
            metadata_tag = opf_tree.find('.//opf:metadata', namespaces=NAMESPACES)
            if metadata_tag is not None:
                new_elem = etree.SubElement(metadata_tag, f"{{{NAMESPACES['dc']}}}identifier")
                new_elem.text = f"urn:isbn:{isbn}"
                # Standard EPUB property for the primary ID
                new_elem.set(f"{{{NAMESPACES['opf']}}}scheme", "ISBN")

    def get_cover(self, path: Union[str, Path]) -> Optional[bytes]:
        """Extract the cover image bytes from an EPUB file."""
        path = Path(path)
        try:
            with zipfile.ZipFile(path, 'r') as zin:
                rootfile_path, opf_tree = self._get_opf_info(zin)
                root_dir = str(Path(rootfile_path).parent)
                
                cover_href = self._find_cover_href(opf_tree)
                if cover_href:
                    image_path = cover_href if root_dir == '.' else str(Path(root_dir) / cover_href)
                    return zin.read(image_path.replace('\\', '/'))
        except Exception as e:
            logger.debug(f"Cover not found in {path}: {e}")
        return None

    def _find_cover_href(self, opf_tree) -> Optional[str]:
        """Attempts to find the cover href using EPUB 3 and EPUB 2 strategies."""
        # EPUB 3
        cover_items = opf_tree.xpath('//opf:item[contains(@properties, "cover-image")]/@href', namespaces=NAMESPACES)
        if cover_items:
            return cover_items[0]
        # EPUB 2
        cover_id = opf_tree.xpath('//opf:meta[@name="cover"]/@content', namespaces=NAMESPACES)
        if cover_id:
            cover_node = opf_tree.xpath(f'//opf:item[@id="{cover_id[0]}"]/@href', namespaces=NAMESPACES)
            if cover_node:
                return cover_node[0]
        return None

    def update_cover(self, path: Union[str, Path], image_path: Optional[str]):
        """Updates or removes the cover image."""
        def update_logic(opf_tree, rootfile_path):
            root_dir = Path(rootfile_path).parent
            cover_href = self._find_cover_href(opf_tree)
            
            internal_img_path = None
            if cover_href:
                full_img_path = root_dir / cover_href if str(root_dir) != '.' else Path(cover_href)
                internal_img_path = str(full_img_path).replace('\\', '/')

            img_data = None
            if image_path:
                with open(image_path, 'rb') as f:
                    img_data = f.read()
            else:
                # Removal: Clean up OPF references
                for node in opf_tree.xpath('//opf:item[contains(@properties, "cover-image")]', namespaces=NAMESPACES):
                    node.getparent().remove(node)
                for node in opf_tree.xpath('//opf:meta[@name="cover"]', namespaces=NAMESPACES):
                    node.getparent().remove(node)
            
            img_update = None
            if internal_img_path:
                img_update = {'path': internal_img_path, 'new_data': img_data}
                
            return opf_tree, img_update

        self._update_epub_zip(path, update_logic)

    def fetch_metadata_by_isbn(self, isbn: str, provider: str = "google") -> Dict[str, Any]:
        """Fetches book metadata from the selected provider."""
        isbn = "".join(filter(str.isdigit, isbn))
        if not isbn: return {}
        
        if provider == "openlibrary":
            return self._fetch_openlibrary(isbn)
        return self._fetch_google(isbn)

    def _fetch_google(self, isbn: str) -> Dict[str, Any]:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                if data.get("totalItems", 0) > 0:
                    item = data["items"][0]
                    info = item["volumeInfo"]
                    return {
                        "title": info.get("title", ""),
                        "author": ", ".join(info.get("authors", [])),
                        "publisher": info.get("publisher", ""),
                        "date": info.get("publishedDate", ""),
                        "isbn": isbn,
                        "cover_url": info.get("imageLinks", {}).get("thumbnail", "").replace("http://", "https://")
                    }
        except urllib.error.HTTPError as e:
            if e.code in (503, 504, 429):
                raise NetworkError(f"Google Books service is temporarily unavailable (HTTP {e.code})")
            logger.error(f"Google Books HTTP error {e.code}: {e}")
        except urllib.error.URLError as e:
            raise NetworkError(f"Connection to Google Books failed: {e.reason}")
        except Exception as e:
            logger.error(f"Google Books fetch failed: {e}")
        return {}

    def _fetch_openlibrary(self, isbn: str) -> Dict[str, Any]:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                key = f"ISBN:{isbn}"
                if key in data:
                    info = data[key]
                    return {
                        "title": info.get("title", ""),
                        "author": ", ".join([a.get("name", "") for a in info.get("authors", [])]),
                        "publisher": ", ".join([p.get("name", "") for p in info.get("publishers", [])]),
                        "date": info.get("publish_date", ""),
                        "isbn": isbn,
                        "cover_url": info.get("cover", {}).get("large", "")
                    }
        except urllib.error.HTTPError as e:
            if e.code in (503, 504, 429):
                raise NetworkError(f"Open Library service is temporarily unavailable (HTTP {e.code})")
            logger.error(f"Open Library HTTP error {e.code}: {e}")
        except urllib.error.URLError as e:
            raise NetworkError(f"Connection to Open Library failed: {e.reason}")
        except Exception as e:
            logger.error(f"Open Library fetch failed: {e}")
        return {}