# import os
# import re
# import glob
# import pandas as pd
# from paddleocr import PaddleOCR
#
#
# class InvoiceProcessorPipeline:
#     def __init__(self, input_dir, output_csv="output.csv"):
#         self.input_dir = input_dir
#         self.output_csv = output_csv
#
#         # Initialize PaddleOCR engine using updated parameters
#         print("Initializing PaddleOCR Engine...")
#         self.ocr = PaddleOCR(use_textline_orientation=True, lang='en')
#
#         # Regex extraction rules for fixed layouts
#         self.rules = {
#             "invoice_number": re.compile(r'(?:invoice\s*num(?:ber)?|inv\s*#|faktura\s*nr)[:.\s-]+([A-Z0-9/\-]+)',
#                                          re.IGNORECASE),
#             "invoice_date": re.compile(
#                 r'(?:invoice\s*date|date|data\s*wystawienia)[:.\s-]+(\d{2}[-./]\d{2}[-./]\d{4}|\d{4}[-./]\d{2}[-./]\d{2})',
#                 re.IGNORECASE),
#             "seller_tax_id": re.compile(
#                 r'(?:seller\s*tax\s*id|seller\s*tin|nip\s*sprzedawcy|seller\s*vat)[:.\s-]+([A-Z0-9\-]{8,15})',
#                 re.IGNORECASE),
#             "client_tax_id": re.compile(
#                 r'(?:client\s*tax\s*id|client\s*tin|nip\s*nabywcy|client\s*vat)[:.\s-]+([A-Z0-9\-]{8,15})',
#                 re.IGNORECASE),
#             "net_worth": re.compile(r'(?:net\s*worth|net\s*total|netto|amount\s*net)[:.\s-]+([0-9.,\s]+)',
#                                     re.IGNORECASE),
#             "vat": re.compile(r'(?:vat|tax|podatek\s*vat)[:.\s-]+([0-9.,\s]+)', re.IGNORECASE),
#             "gross_worth": re.compile(r'(?:gross\s*worth|gross\s*total|brutto|total\s*gross)[:.\s-]+([0-9.,\s]+)',
#                                       re.IGNORECASE)
#         }
#
#     def extract_structured_text(self, image_path):
#         """Extracts text regions using the updated PaddleOCR pipeline interface."""
#         # Removed the deprecated 'cls=True' parameter to prevent execution crash
#         result = self.ocr.ocr(image_path)
#         lines = []
#
#         if result:
#             for page in result:
#                 if page:
#                     for line in page:
#                         # Handle modern PaddleX/PaddleOCR structures safely
#                         if isinstance(line, dict) and "text" in line:
#                             lines.append(str(line["text"]).strip())
#                         elif isinstance(line, (list, tuple)) and len(line) > 1:
#                             # Traditional format: [ [coords], (text, confidence) ]
#                             text_block = line[1]
#                             if isinstance(text_block, (list, tuple)):
#                                 lines.append(str(text_block[0]).strip())
#                             else:
#                                 lines.append(str(text_block).strip())
#         return lines
#
#     def parse_invoice_fields(self, lines, filename):
#         """Applies proximity-based text heuristics to find target layout blocks."""
#         extracted = {
#             "Seller Name": "N/A", "Seller Tax ID": "N/A",
#             "Client Name": "N/A", "Client Tax ID": "N/A",
#             "Invoice Number": "N/A", "Invoice Date": "N/A",
#             "Net Worth": "N/A", "VAT": "N/A", "Gross Worth": "N/A"
#         }
#
#         full_text_block = "\n".join(lines)
#         field_mapping = {
#             "invoice_number": "Invoice Number", "invoice_date": "Invoice Date",
#             "seller_tax_id": "Seller Tax ID", "client_tax_id": "Client Tax ID",
#             "net_worth": "Net Worth", "vat": "VAT", "gross_worth": "Gross Worth"
#         }
#
#         # 1. Regex Mapping
#         for key, regex in self.rules.items():
#             match = regex.search(full_text_block)
#             if match:
#                 extracted[field_mapping[key]] = match.group(1).strip(":-. ")
#
#         # 2. Key-Label Contextual Neighborhood Mapping (Names)
#         for i, line in enumerate(lines):
#             # Resolve Seller Name (Usually sits exactly above/below the Tax ID or Vendor Label)
#             if extracted["Seller Tax ID"] != "N/A" and extracted["Seller Tax ID"] in line:
#                 if i > 0 and not any(x in lines[i - 1].lower() for x in ["seller", "tax", "nip"]):
#                     extracted["Seller Name"] = lines[i - 1]
#             elif "seller" in line.lower() or "sprzedawca" in line.lower():
#                 if i + 1 < len(lines) and len(lines[i + 1]) > 3:
#                     extracted["Seller Name"] = lines[i + 1]
#
#             # Resolve Client Name
#             if extracted["Client Tax ID"] != "N/A" and extracted["Client Tax ID"] in line:
#                 if i > 0 and not any(x in lines[i - 1].lower() for x in ["client", "tax", "nip", "buyer"]):
#                     extracted["Client Name"] = lines[i - 1]
#             elif "client" in line.lower() or "buyer" in line.lower():
#                 if i + 1 < len(lines) and len(lines[i + 1]) > 3:
#                     extracted["Client Name"] = lines[i + 1]
#
#         return extracted
#
#     def run(self):
#         """Scans folder, isolates assessment range unique files, and runs OCR pipeline."""
#         extensions = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
#         all_images = []
#         for ext in extensions:
#             all_images.extend(glob.glob(os.path.join(self.input_dir, ext)))
#
#         # Use a set to prevent processing duplicate paths due to case-insensitive file extensions
#         unique_paths = sorted(list(set(os.path.abspath(p) for p in all_images)))
#         target_images = []
#
#         for path in unique_paths:
#             basename = os.path.basename(path)
#             # Match both batch1-XXXX and batch1_XXXX variations
#             match = re.search(r'batch1[-_](\d{4})', basename, re.IGNORECASE)
#             if match:
#                 file_num = int(match.group(1))
#                 # Restrict strictly to assessment target files: 0331 to 0381 (50 files total)
#                 if 331 <= file_num <= 381:
#                     target_images.append(path)
#
#         if len(target_images) == 0:
#             print(f"❌ Found 0 target files in: {self.input_dir}")
#             print("Double check that your path points exactly to the folder containing 'batch1-0331.jpg'.")
#             return
#
#         print(f"✅ Target files identified! Processing {len(target_images)} unique invoice images...")
#
#         dataset_records = []
#         for idx, img_path in enumerate(target_images):
#             filename = os.path.basename(img_path)
#             print(f"[{idx + 1}/{len(target_images)}] Parsing data matrix for: {filename}")
#
#             try:
#                 extracted_lines = self.extract_structured_text(img_path)
#                 record = self.parse_invoice_fields(extracted_lines, filename)
#                 record_with_meta = {"File Name": filename, **record}
#                 dataset_records.append(record_with_meta)
#             except Exception as e:
#                 print(f"⚠️ Extraction error on {filename}: {str(e)}")
#                 dataset_records.append({"File Name": filename})
#
#         # Save table matrix data back to project root workspace
#         df = pd.DataFrame(dataset_records)
#         df.to_csv(self.output_csv, index=False)
#         print(f"\n🎉 Success! Extracted metrics exported to: '{os.path.abspath(self.output_csv)}'")
#
#
# if __name__ == "__main__":
#     # Ensure this points exactly to your unzipped batch1_1 folder containing your image subset
#     DIR_PATH = r"E:\Image_Details\batch_1\batch_1\batch1_1"
#
#     if not os.path.exists(DIR_PATH):
#         print(f"❌ ERROR: The directory path '{DIR_PATH}' does not exist on your machine.")
#     else:
#         processor = InvoiceProcessorPipeline(input_dir=DIR_PATH, output_csv="output.csv")
#         processor.run()

import os
import re
import glob
import pandas as pd
from paddleocr import PaddleOCR


class InvoiceProcessorPipeline:
    def __init__(self, input_dir, output_csv="output.csv"):
        self.input_dir = input_dir
        self.output_csv = output_csv

        # Initialize PaddleOCR engine using updated parameters
        print("Initializing PaddleOCR Engine...")
        self.ocr = PaddleOCR(use_textline_orientation=True, lang='en')

        # Regex extraction rules for fixed layouts
        self.rules = {
            "invoice_number": re.compile(r'(?:invoice\s*num(?:ber)?|inv\s*#|faktura\s*nr)[:.\s-]+([A-Z0-9/\-]+)',
                                         re.IGNORECASE),
            "invoice_date": re.compile(
                r'(?:invoice\s*date|date|data\s*wystawienia)[:.\s-]+(\d{2}[-./]\d{2}[-./]\d{4}|\d{4}[-./]\d{2}[-./]\d{2})',
                re.IGNORECASE),
            "seller_tax_id": re.compile(
                r'(?:seller\s*tax\s*id|seller\s*tin|nip\s*sprzedawcy|seller\s*vat)[:.\s-]+([A-Z0-9\-]{8,15})',
                re.IGNORECASE),
            "client_tax_id": re.compile(
                r'(?:client\s*tax\s*id|client\s*tin|nip\s*nabywcy|client\s*vat)[:.\s-]+([A-Z0-9\-]{8,15})',
                re.IGNORECASE),
            "net_worth": re.compile(r'(?:net\s*worth|net\s*total|netto|amount\s*net)[:.\s-]+([0-9.,\s]+)',
                                    re.IGNORECASE),
            "vat": re.compile(r'(?:vat|tax|podatek\s*vat)[:.\s-]+([0-9.,\s]+)', re.IGNORECASE),
            "gross_worth": re.compile(r'(?:gross\s*worth|gross\s*total|brutto|total\s*gross)[:.\s-]+([0-9.,\s]+)',
                                      re.IGNORECASE)
        }

    def extract_structured_text(self, image_path):
        """Extracts text regions using the updated PaddleOCR pipeline interface."""
        # Removed the deprecated 'cls=True' parameter to prevent execution crash
        result = self.ocr.ocr(image_path)
        lines = []

        if result:
            for page in result:
                if page:
                    for line in page:
                        # Handle modern PaddleX/PaddleOCR structures safely
                        if isinstance(line, dict) and "text" in line:
                            lines.append(str(line["text"]).strip())
                        elif isinstance(line, (list, tuple)) and len(line) > 1:
                            # Traditional format: [ [coords], (text, confidence) ]
                            text_block = line[1]
                            if isinstance(text_block, (list, tuple)):
                                lines.append(str(text_block[0]).strip())
                            else:
                                lines.append(str(text_block).strip())
        return lines

    def parse_invoice_fields(self, lines, filename):
        """Applies hardened context mapping with overwrite protection."""
        extracted = {
            "Seller Name": "N/A", "Seller Tax ID": "N/A",
            "Client Name": "N/A", "Client Tax ID": "N/A",
            "Invoice Number": "N/A", "Invoice Date": "N/A",
            "Net Worth": "N/A", "VAT": "N/A", "Gross Worth": "N/A"
        }

        # Strictly isolate line-by-line boundaries to prevent vertical leakage
        field_mapping = {
            "invoice_number": "Invoice Number", "invoice_date": "Invoice Date",
            "seller_tax_id": "Seller Tax ID", "client_tax_id": "Client Tax ID",
            "net_worth": "Net Worth", "vat": "VAT", "gross_worth": "Gross Worth"
        }

        # 1. Row-by-Row Strict Regex Execution
        for i, line in enumerate(lines):
            for key, regex in self.rules.items():
                # Check if target key is still unassigned before evaluation
                target_field = field_mapping[key]
                if extracted[target_field] == "N/A":
                    match = regex.search(line)
                    if match:
                        extracted[target_field] = match.group(1).strip(":-. ")

        # 2. Protected Structural Proximity Fallbacks
        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Resolve Seller Name with strict extraction protection
            if extracted["Seller Name"] == "N/A":
                if extracted["Seller Tax ID"] != "N/A" and extracted["Seller Tax ID"] in line:
                    if i > 0 and not any(x in lines[i - 1].lower() for x in ["seller", "tax", "nip", "sprzedawca"]):
                        extracted["Seller Name"] = lines[i - 1].strip()
                elif any(x in line_lower for x in ["seller", "sprzedawca"]):
                    if i + 1 < len(lines) and len(lines[i + 1]) > 3 and not any(
                            x in lines[i + 1].lower() for x in ["tax", "nip"]):
                        extracted["Seller Name"] = lines[i + 1].strip()

            # Resolve Client Name with strict extraction protection
            if extracted["Client Name"] == "N/A":
                if extracted["Client Tax ID"] != "N/A" and extracted["Client Tax ID"] in line:
                    if i > 0 and not any(
                            x in lines[i - 1].lower() for x in ["client", "tax", "nip", "buyer", "nabywca"]):
                        extracted["Client Name"] = lines[i - 1].strip()
                elif any(x in line_lower for x in ["client", "buyer", "nabywca"]):
                    if i + 1 < len(lines) and len(lines[i + 1]) > 3 and not any(
                            x in lines[i + 1].lower() for x in ["tax", "nip"]):
                        extracted["Client Name"] = lines[i + 1].strip()

        return extracted

    def run(self):
        """Scans folder, isolates assessment range unique files, and runs OCR pipeline."""
        extensions = ('*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG')
        all_images = []
        for ext in extensions:
            all_images.extend(glob.glob(os.path.join(self.input_dir, ext)))

        # Use a set to prevent processing duplicate paths due to case-insensitive file extensions
        unique_paths = sorted(list(set(os.path.abspath(p) for p in all_images)))
        target_images = []

        for path in unique_paths:
            basename = os.path.basename(path)
            # Match both batch1-XXXX and batch1_XXXX variations
            match = re.search(r'batch1[-_](\d{4})', basename, re.IGNORECASE)
            if match:
                file_num = int(match.group(1))
                # Restrict strictly to assessment target files: 0331 to 0381 (50 files total)
                if 331 <= file_num <= 381:
                    target_images.append(path)

        if len(target_images) == 0:
            print(f" Found 0 target files in: {self.input_dir}")
            print("Double check that your path points exactly to the folder containing 'batch1-0331.jpg'.")
            return

        print(f" Target files identified! Processing {len(target_images)} unique invoice images...")

        dataset_records = []
        for idx, img_path in enumerate(target_images):
            filename = os.path.basename(img_path)
            print(f"[{idx + 1}/{len(target_images)}] Parsing data matrix for: {filename}")

            try:
                extracted_lines = self.extract_structured_text(img_path)
                record = self.parse_invoice_fields(extracted_lines, filename)
                record_with_meta = {"File Name": filename, **record}
                dataset_records.append(record_with_meta)
            except Exception as e:
                print(f" Extraction error on {filename}: {str(e)}")
                dataset_records.append({"File Name": filename})

        # Save table matrix data back to project root workspace
        df = pd.DataFrame(dataset_records)
        df.to_csv(self.output_csv, index=False)
        print(f"\n Success! Extracted metrics exported to: '{os.path.abspath(self.output_csv)}'")


if __name__ == "__main__":
    # Ensure this points exactly to your unzipped batch1_1 folder containing your image subset
    DIR_PATH = r"E:\Image_Details\batch_1\batch_1\batch1_1"

    if not os.path.exists(DIR_PATH):
        print(f" ERROR: The directory path '{DIR_PATH}' does not exist on your machine.")
    else:
        processor = InvoiceProcessorPipeline(input_dir=DIR_PATH, output_csv="output.csv")
        processor.run()

