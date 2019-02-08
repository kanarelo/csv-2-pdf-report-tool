import os
import time

from pdf_utils import generate_report_book

import logging
logger = logging.getLogger('weasyprint')
logger.addHandler(logging.FileHandler('weasyprint.log'))

class Report(object):
    @staticmethod
    def generate(output_directory='final_reports', file_name='comprehensive_report.pdf'):
        
        print("-" * 50)
        print("Reading CSV files to generate reports")
        time.sleep(1)
        print("Generating PDF files, please be patient, we'll be done in a minute or two")
        time.sleep(1)
        print("-" * 50)
        
        pdf_binary = generate_report_book()
        print("PDF report generation complete")


if __name__ == "__main__":
    Report.generate()
