import zipfile
from lxml import etree
import fitz
import re, subprocess, os
from common.s3_operations import S3Helper
from common.logs import logger
from scripts.check_doc_names import extract_bookmark_references, extract_links_and_references_pages
from pathlib import Path
from docx2pdf import convert
import pythoncom
from scripts.terminate_active_COM import terminate_active_processes
import os
import time
from common.s3_operations import S3Helper
import win32com
from scripts.toc import toc_errors

def find_git_root(start_path: Path) -> Path:
    """Finds the root of the Git repository by looking for the .git folder."""
    current_path = start_path.resolve()

    while current_path != current_path.parent:  # Stop at the drive root (C:\, D:\, etc.)
        if (current_path / ".git").exists():  # Check if .git folder exists
            return current_path
        current_path = current_path.parent  # Move up one level

    raise FileNotFoundError("Git repository root not found. Ensure the script is inside a Git repo.")

# Get the repo root (starting search from the script's location)
repo_root = find_git_root(Path(__file__).parent)
TMP_DIR = repo_root / "s3_downloads"

# Create the directory if it doesn’t exist
TMP_DIR.mkdir(parents=True, exist_ok=True)

def extract_bookmarks_and_citations_from_docx(file_path):
    """
    Extract bookmarks and their associated text, along with citations (hyperlinks) and their destination text from a DOCX file.

    :param docx_path: Path to the DOCX file
    :return: Dictionary with bookmarks and citations
    """
    try:
        result = {
            "bookmarks": [],
            "citations": []
        }

        if file_path.startswith('s3://'):
                s3_bucket = file_path.split('/')[2]
                s3_helper = S3Helper(s3_bucket)
                s3_key = '/'.join(file_path.split('/')[3:])
                ts = str(time.time()).replace('.', '_')
                local_key = list(s3_key.split('.'))
                local_key[0] += f'_{ts}'
                local_key = '.'.join(local_key)
                local_file_path = os.path.join(TMP_DIR, os.path.basename(local_key))
                s3_helper.download_file_from_s3(s3_key, local_file_path)
                file_path = local_file_path

        logger.info(str(f'Starting to extract bookmarks from the document ')+'[extract_bookmarks_and_citations_from_docx] [scripts/validate_references.py:34]')
        # Open the DOCX file as a zip archive
        print(f"Using file: {file_path}")
        (f"Last modified: {os.path.getmtime(file_path)}")
        with zipfile.ZipFile(file_path, 'r') as z:
            # Extract the main document XML
            z.testzip()
            with z.open('word/document.xml') as f:
                document_xml_content = f.read()
            # Extract the relationships file for hyperlinks
            with z.open('word/_rels/document.xml.rels') as f:
                relationships_xml_content = f.read()
        
        logger.info(str('Parsing xml structure ')+'[extract_bookmarks_and_citations_from_docx] [scripts/validate_references.py:44]')
        # Parse the XML content using lxml
        print(document_xml_content)
        print(relationships_xml_content)
        parser = etree.XMLParser(recover=True, remove_blank_text=True)
        doc_root = etree.fromstring(document_xml_content, parser)
        rel_root = etree.fromstring(relationships_xml_content, parser)
        
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
                    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
        
        # Build a dictionary of relationship IDs to URLs
        rels = {
            rel.get('Id'): rel.get('Target') for rel in rel_root.findall('.//Relationship')
        }

        logger.info(str(f'Relations between IDs and URLs established ')+'[extract_bookmarks_and_citations_from_docx] [scripts/validate_references.py:57]')
        # Extract bookmarks
        for bookmark_start in doc_root.findall('.//w:bookmarkStart', namespace):
            bookmark_name = bookmark_start.get(f'{{{namespace["w"]}}}name')
            
            # Now gather the text between the bookmarkStart and bookmarkEnd
            parent = bookmark_start.getparent()
            bookmark_text = ""
            
            # Collect text nodes after bookmarkStart and before bookmarkEnd
            current_element = bookmark_start.getnext()
            while current_element is not None:
                if current_element.tag.endswith("bookmarkEnd") and current_element.get(f'{{{namespace["w"]}}}id') == bookmark_start.get(f'{{{namespace["w"]}}}id'):
                    break
                # Check if the element is a 't' (text) element or part of a 'r' (run) element
                if current_element.tag.endswith("t"):  # If the tag is text
                    bookmark_text += current_element.text or ""
                elif current_element.tag.endswith("r"):  # If it is a 'run' (r) element, check for nested text
                    for sub_elem in current_element.iter():
                        if sub_elem.tag.endswith("t"):
                            bookmark_text += sub_elem.text or ""
                current_element = current_element.getnext()
            # print(bookmark_text)
            bookmark_name = bookmark_start.get(f'{{{namespace["w"]}}}name')
            # Locate the text node immediately following the bookmark
            parent = bookmark_start.getparent()
            destination_text = ""
            if parent is not None:
                for sibling in parent.iter():
                    if sibling.tag.endswith("t"):  # If the tag is text
                        destination_text += sibling.text or ""
            
            result["bookmarks"].append({
                'bookmark_name': bookmark_name,
                'destination_text': destination_text.strip() if len(destination_text.strip()) < 200 else "Invalid link format",
                'bookmark_text': bookmark_text
            })
        
        logger.info(str('Bookmarks extracted. ')+'[extract_bookmarks_and_citations_from_docx] [scripts/validate_references.py:95]')
        # Extract citations (hyperlinks)
        for hyperlink in doc_root.findall('.//w:hyperlink', namespace):
            # Get the relationship ID for the hyperlink
            rel_id = hyperlink.get(f'{{{namespace["r"]}}}id')
            link = rels.get(rel_id, None)  # Resolve the URL from relationships
            
            # Extract the text associated with the hyperlink
            citation_text = ""
            for child in hyperlink.iter():
                if child.tag.endswith("t"):  # If the tag is text
                    citation_text += child.text or ""
            
            # Extract the destination text following the hyperlink
            destination_text = ""
            parent = hyperlink.getparent()
            if parent is not None:
                for sibling in parent.iter():
                    if sibling.tag.endswith("t") and sibling not in hyperlink.iter():
                        destination_text += sibling.text or ""
            
            if citation_text and link:
                result["citations"].append({
                    'citation_text': citation_text.strip(),
                    'link': link,
                    'destination_text': destination_text.strip() if len(destination_text.strip()) < 200 else "Invalid link format"
                })
            # print(result)
        return result
    
    except Exception as e:
        logger.error(str(f'Encounterd error while extracting bookmarks ')+'[extract_bookmarks_and_citations_from_docx] [scripts/validate_references.py:126]')
        raise Exception(str(f'{e}'))

def convert_docx_to_pdf(file_path) -> str:
        """Convert document to PDF using Microsoft Office COM automation"""
        output_dir = os.path.dirname(file_path)
        pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(file_path))[0] + '.pdf')

        try:
            # Try using win32com for Word to PDF conversion
            try:
                terminate_active_processes()
                pythoncom.CoInitialize() 
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(file_path)
                doc.SaveAs(pdf_file, FileFormat=17)  # 17 represents PDF format
                return pdf_file
            except Exception as e:
                logger.error(f"COM automation failed: {str(e)}")

                # Fallback to alternative conversion methods
                try:
                    # Try using docx2pdf if available
                    convert(file_path, pdf_file)
                    return pdf_file
                except ImportError:
                    # Last resort: Try using system installed Office
                    soffice_paths = [
                        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
                        r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE",
                    ]

                    for soffice_path in soffice_paths:
                        if os.path.exists(soffice_path):
                            command = [
                                soffice_path,
                                "/q",
                                "/n",
                                "/f",
                                "/c",
                                f"SaveAs.PDF({pdf_file})",
                                file_path
                            ]
                            subprocess.run(command, check=True)
                            return pdf_file

                    raise Exception("No viable PDF conversion method found")

        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise
        
        finally:
            try:
                if doc:
                    doc.Close()
                    del doc
            except Exception as e:
                logger.error(str('Error deleting doc ')+'[convert to pdf] [scripts\margin_check.py:137]')
            try:
                if word:
                    word.Quit()
                    del word
            except Exception as e:
                logger.error(str('Error deleting word app ')+'[convert to pdf] [scripts\margin_check.py:143]')
            pythoncom.CoUninitialize()

# def convert_docx_to_pdf(docx_file):
#     # Deriving the PDF output file path in the same directory as the input file
#     terminate_active_processes()
#     pythoncom.CoInitialize()
#     try:
#         logger.info(str(f'Converting docx to pdf ')+'[convert_docx_to_pdf] [scripts/validate_references.py:131]')
#         if not os.path.exists(docx_file):
#             raise FileNotFoundError(f"The file {docx_file} does not exist.")
        
#         output_dir = os.path.dirname(docx_file)  # Directory of the input file
#         pdf_file = os.path.join(output_dir, os.path.splitext(os.path.basename(docx_file))[0] + '.pdf')
#         # Running the LibreOffice command to convert to PDF
#         convert(docx_file, output_dir)
#         logger.info(str(f'Converion of pdf successful ')+'[convert_docx_to_pdf] [scripts/validate_references.py:145]')
        
#         return pdf_file
    
#     except Exception as e:
#         logger.error(str(f'Encountered the following error while converting to pdf - {e}')+'[convert_docx_to_pdf] [scripts/validate_references.py:151]')
#         raise Exception(f'{e}')
    
#     finally:
#         pythoncom.CoUninitialize()

# Function to extract heading numbers from PDF
def extract_headings_from_pdf(pdf_file, headings):
    try:
        doc = fitz.open(pdf_file)
        
        # Extract all text from the entire PDF document
        full_text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            full_text += page.get_text("text")
        
        logger.info(str('Text extracted, searching for headings ')+'[extract_headings_from_pdf] [scripts/validate_references.py:165]')
        matched_headings = {}
        
        # Loop through the headings extracted from docx
        for heading_text in headings:
            if len(heading_text[0].strip())> 0:
            # Use the entire heading text (number and name) to search for matches in the PDF
                heading_regex = re.escape(heading_text[0])   # Escape any special characters in the heading text
                
                # Search the entire PDF text for matches of the heading number and name
                matches = re.findall(rf"(?<!\S)(\d+(?:\.\d+)*\.?)\s*(.*){heading_regex}", full_text)
            
                
                if matches:
                    if matches[-1][1] == '':
                        matched_headings[heading_text[0]] = matches[-1][0]
                    else:
                        matched_headings[heading_text[0]] = matches[-1][1].strip()
                else:
                    matched_headings[heading_text[0]] = None
        
        logger.info(str('Headings extracted')+' [extract_headings_from_pdf] [scripts/validate_references.py:186]')        
        return matched_headings
    
    except Exception as e:
        logger.error(str(f'Encountered the following error while extracting heading - {e} ')+'[extract_headings_from_pdf] [scripts/validate_references.py:190]')
        raise Exception(str(f'{e}'))
    

def verify_references(docx_path):
    try:
        if docx_path.startswith('s3'):
                s3_bucket = docx_path.split('/')[2]
                s3_helper = S3Helper(s3_bucket)
                s3_key = '/'.join(docx_path.split('/')[3:])
                local_file_path = os.path.join(TMP_DIR, os.path.basename(s3_key))
                    # Download the file from S3
                s3_helper.download_file_from_s3(s3_key, local_file_path)
                docx_path =  local_file_path

        data = extract_bookmarks_and_citations_from_docx(docx_path)
        llist = extract_bookmark_references(docx_path)
        # pdf_file = convert_docx_to_pdf(docx_path)
        # pdf_file = "C:\\Users\\Yash\\Downloads\\Test3_BRKT (1) - test.pdf"
        page_nums, headings, final_list = extract_links_and_references_pages(docx_path)
        logger.info(str('Getting TOC errors')+'[methodName] [scripts\validate_references.py:307]')
        taoc=toc_errors(data,page_nums,llist)
        logger.info(str('Fetched TOC errors')+'[methodName] [scripts\validate_references.py:309]')
        # print(page_nums)
        # print(data, llist)
        errors = []
        logger.info(str('Extracting errors ')+'[verify_bookmarks] [scripts/validate_references.py:201]')
        for final_bookmark in final_list:
            print(final_bookmark)
            for ref in data["bookmarks"]:
                if ref["bookmark_name"] == final_bookmark["reference"]:
                    bookmark = ref
                    print(bookmark)
                    break
            print('---------------------------------------------------------------------------------------------------')    
            # name = [item[1] for item in llist if item[0]==bookmark["bookmark_name"]]
            

            name = final_bookmark["reference_text"]
            if not '_Toc' in final_bookmark["reference"]:
                if len(name) > 0:
                    page_num = final_bookmark["page_number"]
                    # if page_num:
                    #     page_num = list(page_num)[0]
                    # else:
                    #     for k, v in page_nums.items():
                    #         if bookmark["bookmark_name"] in k:
                    #             page_num = list(v)[0]
                    #             break

                    if name.strip() not in bookmark["destination_text"].strip() and page_num:
                        if re.findall(r'(?<!\S)(\d+(?:\.\d+)*\.?)\s*(.*)', name):
                            matched_headings = []
                            name_num = re.findall(r'(?<!\S)(\d+(?:\.\d+)*\.?)\s*(.*)', name)[0][0]
                            print(f' number in name : {name_num}')
                            for h, number, page in headings:
                                if number:
                                    # print(number, h, name[0])
                                    number = number.replace('.', ' ').strip()
                                    ref_name = name_num.replace('.', ' ').strip()
                                    if ref_name in number:
                                        print(number, h, name)
                                        matched_headings.append(h)
                            # matched_headings = extract_headings_from_pdf(pdf_file, [(bookmark["destination_text"].strip(), None)])
                            if matched_headings:
                                if not any(bookmark["destination_text"].replace(' ', '') in heading.replace(' ', '') for heading in matched_headings):
                                    logger.info(str(f"Citation for {bookmark} does not match {name}")+' [verify_references] [scripts/validate_references.py:210]')
                                    # errors.append(f"Citation for {name[0]} does not match {bookmark['destination_text']}")
                                    errors.append({"document_text": name, "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})
                                else:
                                    errors.append({"document_text": name, "referenced_text": bookmark['destination_text'], "has_error": False, "page": page_num})
                            else:
                                logger.info(str(f"Citation for {bookmark} does not match {name}")+' [verify_references] [scripts/validate_references.py:210]')
                                    # errors.append(f"Citation for {name[0]} does not match {bookmark['destination_text']}")
                                errors.append({"document_text": name, "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})
                        
                        else:
                            logger.info(str(f"Citation for {name} does not match {bookmark['destination_text']}")+'[verify_references] [scripts/validate_references.py:215]')
                            # errors.append(f"Citation for {name[0]} does not match {bookmark['destination_text']}")
                            errors.append({"document_text": name, "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})
                    elif page_num:
                        if name or bookmark["destination_text"]:
                            errors.append({"document_text": name, "referenced_text": bookmark['destination_text'], "has_error": False, "page": page_num})
                else:
                    if bookmark["bookmark_name"]:
                        page_num = final_bookmark["page_number"]
                        # if page_num:
                        #     page_num = list(page_num)[0]
                        if not bookmark["bookmark_text"].strip() in bookmark["destination_text"].strip() and page_num:
                            logger.info(str(f"Citation for {bookmark} does not match {bookmark['destination_text']}")+' [verify_references] [scripts/validate_references.py:221]')
                            # errors.append(f"Citation for {bookmark} does not match {bookmark['destination_text']}")
                            errors.append({"document_text": bookmark["bookmark_text"], "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})
                        elif page_num:
                            if bookmark["bookmark_text"] and bookmark["destination_text"]:
                                if bookmark["bookmark_text"] and (bookmark["bookmark_text"] not in bookmark["destination_text"]):
                                    errors.append({"document_text": bookmark["bookmark_text"], "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})
                                else:
                                    errors.append({"document_text": bookmark["bookmark_text"], "referenced_text": bookmark['destination_text'], "has_error": False, "page": page_num})
                            else:
                                if bookmark["bookmark_text"] or bookmark["destination_text"]:
                                    errors.append({"document_text": bookmark["bookmark_text"], "referenced_text": bookmark['destination_text'], "has_error": True, "page": page_num})

        logger.info(str(f'Errors extracted. found - {len(errors)} errors ')+'[verify_errors] [scripts/validate_references.py:225]')
        # print(taoc)
        return errors,taoc
    
    except Exception as e:
        logger.error(str(f'{e}')+' [verify_references] [scripts/validate_references.py:229]')
        raise Exception(str(f'{e}'))
    
    finally:
        # if os.path.exists(pdf_file):
        #     os.remove(pdf_file)
        if os.path.exists(docx_path):
            print("Deleting")
            os.remove(docx_path)
