import os
import time

from pdf_utils import \
    generate_pdf_reportbook, generate_condensed_pdf

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
        
        pdf_binary = generate_condensed_pdf()
        print("PDF report generation complete")

        # for report_image in generate_condensed_pdf():
        #     report_image.image.save(f"{output_directory}/{report_image.report.report_name}-{report_image.report.period}.png", "PNG", resolution=100)

            # output_filename = os.path.join(os.path.dirname(__file__), output_directory, file_name)
            # with open(output_filename, 'wb') as output_file:
            #     output_file.write(pdf_binary)


if __name__ == "__main__":
    Report.generate()
