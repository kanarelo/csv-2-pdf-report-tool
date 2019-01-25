import os

import base64
import jinja2
import io
import pdfkit
import PyPDF2 as pyPdf

from reports import generate_report_context
from tempfile import NamedTemporaryFile

from PIL import Image as PILImage, ImageChops, ImageDraw
from pdf2image import convert_from_bytes

import numpy as np
from collections import namedtuple, OrderedDict

import weasyprint
import utils

def get_periods():
    return [
        'week',
        'quarter',
        'period',
        'year'
    ]
    
def get_report_names():
    return [
        'summary',
        'dz_payments', #-0
        'dz_orders',
        'payments',
        'orders', #-1
        'products',
        'traffic',
        'dpp', #-2
        'dpt',
        'upt',
        'tphw', #-3
        'sphw' ]

def get_comparable_reports():
    return [
        'payments',
        'orders',
        'products',
        'traffic',
        'dpp',
        'dpt',
        'upt',
        'tphw',
        'sphw']

def get_totalled_reports(): 
    return [
        'summary', 'orders', 'payments',
        'products', 'dz_orders', 'dz_payments'
    ]

PageMapping = namedtuple('PageMapping', ('page', 'orientation', 'reports'))
def get_page_mappings(start_page=0): 
    return [
        PageMapping((start_page + 1), 'portrait', ['summary', 'dz_payments']),
        PageMapping((start_page + 2), 'portrait', ['dz_orders', 'payments', 'orders']),
        PageMapping((start_page + 3), 'landscape', ['products', 'traffic', 'dpp']),
        PageMapping((start_page + 4), 'landscape', ['dpt', 'upt', 'tphw']),
        PageMapping((start_page + 5), 'portrait', ['sphw'])]

def get_mapping(report_name):
    for page_mapping in get_page_mappings():
        if report_name in page_mapping.reports:
            return page_mapping

def bind_pdf_pages(pages):
    pdf_writer = pyPdf.PdfFileWriter()

    for page in pages:
        pdf_writer.addPage(page)

    with io.BytesIO() as temp:
        pdf_writer.write(temp)

        return temp.getvalue()

ReportMeta = namedtuple('ReportMeta', ('full_report_name', 'short_report_name', 'detailed_caption'))
def get_report_meta(report_name, period):
    period = period if period != 'period' else 'month'

    if period == 'year':
        postfix = 'this year and last year.'
    else:
        postfix = f'this {period}, last {period} and last year same {period}.'

    return {
        'summary': ReportMeta('Summary', 'summary', f'Overview of the main KPIs for the current {period}.'),
        'dz_payments': ReportMeta('Sales per Delivery Region', 'dz_payments', f'Payments made by delivery region, separated by Web/Retail for {postfix}'),
        'dz_orders': ReportMeta('Orders per Delivery Region', 'dz_orders', f'Orders made by delivery region, separated by Web/Retail for {postfix}'),
        'payments': ReportMeta('Sales', 'payments', f'Payments made by store, {postfix}'),
        'orders': ReportMeta('Orders', 'orders', f'Orders made by store, {postfix}'),
        'products': ReportMeta('Products', 'products', f'Products sold (unit) by store, {postfix}'),
        'traffic': ReportMeta('Traffic', 'traffic', f'Visits by store, {postfix}'),
        'dpp': ReportMeta('Dollars Per Product', 'dpp', f'Payments per product sold (unit) by store, {postfix}'),
        'dpt': ReportMeta('Dollars Per Order', 'dpt', f'Payments per product sold (unit) by store, {postfix}'),
        'upt': ReportMeta('Products Per Order', 'upt', f'Payments per order by store, {postfix}'),
        'tphw': ReportMeta('Traffic Per Worked Hours', 'tphw', f'Visits per hour worked by store, {postfix}'),
        'sphw': ReportMeta('Sales Per Worked Hours', 'sphw', f'Sales per hour worked by store, {postfix}'),
    }[report_name]

def generate_pdf_reportbook_reports(report_name=None, period=None):
    Report = namedtuple('Report', (
        'report_name', 
        'pdf_file', 
        'period', 
        'pages', 
        'get_page_mapping', 
        'close_file',
        'get_report_meta'))

    def generate_single_report(report_name, period):
        template_env = utils.get_jinja_template_env()

        (template_name, context) = generate_report_context(
            report_name, 
            period=period, 
            totalled_reports=get_totalled_reports(),
            comparable_reports=get_comparable_reports())

        pdf_template = template_env.get_template('templates/%s' % template_name)
        pdf_html_content = pdf_template.render(**context)

        pdf_temp_file = NamedTemporaryFile(delete=True)
        
        document = get_weasyprint_document(pdf_html_content)
        document.write_pdf(pdf_temp_file.name)

        pdf_file_reader = pyPdf.PdfFileReader(pdf_temp_file)
        pages = [pdf_file_reader.getPage(i) for i in range(pdf_file_reader.getNumPages())]

        return Report(
            report_name, 
            pdf_temp_file, 
            period, 
            pages, 
            lambda: get_mapping(report_name),
            lambda: pdf_temp_file.close(),
            lambda: get_report_meta(report_name, period))

    periods = ((period is not None) and [period] or get_periods())
    report_names = ((report_name is not None) and [report_name] or get_report_names())

    for period in periods:
        for report_name in report_names:
            yield generate_single_report(report_name, period)

def get_weasyprint_document(html_content):
    font_config = weasyprint.fonts.FontConfiguration()
    return weasyprint\
        .HTML(string=html_content)\
        .render(
            stylesheets=[weasyprint.CSS(string=utils.get_css())], 
            font_config=font_config)

def generate_pdf_reportbook(report_name=None, period=None, close_files=False):
    reports = generate_pdf_reportbook_reports(report_name=report_name, period=period)
    final_pdf_binary = bind_pdf_pages(page for report in reports for page in report.pages)

    for report in reports:
        for page in report.pages:
            flat_list.append(page)

    if close_files:
        for report in reports:
            report.pdf_file.close()

    return final_pdf_binary

def get_base64(image, image_format='png', as_string=True):
    if type(image) == str:
        image = PILImage.open(image)
    
    with io.BytesIO() as temp:
        image.save(temp, image_format.upper(), resolution=80)
        temp.seek(0)

        if as_string:
            return f"data:image/{image_format};base64,{base64.b64encode(temp.read()).decode('utf-8')}"

        return temp

def generate_condensed_pdf(period=None, close_files=False):
    template_env = utils.get_jinja_template_env()

    def crop_image(im):
        bg = PILImage.new(im.mode, im.size, im.getpixel((0,0)))
        diff = ImageChops.difference(im, bg)
        diff = ImageChops.add(diff, diff, 2.0, -100)
        bbox = diff.getbbox()

        if bbox:
            return im.crop(bbox)

    def stitch_images(images, max_horiz=np.iinfo(int).max):
        n_images = len(images)
        n_horiz = min(n_images, max_horiz)
        h_sizes, v_sizes = [0] * n_horiz, [0] * (n_images // n_horiz)

        for i, im in enumerate(images):
            h, v = i % n_horiz, i // n_horiz
            h_sizes[h] = max(h_sizes[h], im.size[0])
            v_sizes[v] = max(v_sizes[v], im.size[1])

        h_sizes, v_sizes = np.cumsum([0] + h_sizes), np.cumsum([0] + v_sizes)
        im_grid = PILImage.new('RGB', (h_sizes[-1], v_sizes[-1]), color='white')

        for i, im in enumerate(images):
            im_grid.paste(im, (h_sizes[i % n_horiz], v_sizes[i // n_horiz]))

        return im_grid

    def crop_pdf_image(report_name, image, i=None):
        cropped = crop_image(image)

        if report_name not in ('dz_payments', 'dz_orders', None):
            if i is not None:
                (w, h) = cropped.size
                if i != 0:
                    cropped = cropped.crop((0, 46, w, h))
                else:
                    cropped = cropped.crop((0, 0, w, h - 40))
        
        return cropped

    class ReportImage(object):
        def __init__(self, report, image_number, image):
            self.report = report
            self.image_number = image_number
            self.image  = image

        def get_base64(self):
            return get_base64(self.image)

        @staticmethod
        def generate_pdf_table_of_images(report_name=None, period=None):
            reports = generate_pdf_reportbook_reports(
                report_name=report_name,
                period=period)
                
            for (i, report) in enumerate(reports):
                with report.pdf_file as pdf_file:
                    pdf_file.seek(0)

                    pdf_images = convert_from_bytes(
                        pdf_file.read(), 
                        transparent=True, 
                        use_cropbox=True, 
                        fmt='png')

                    if len(report.pages) > 0:
                        cropped_images = [
                            crop_pdf_image(report_name, pdf_image, i) 
                                for (i, pdf_image) in enumerate(pdf_images) ]
                        final_image = stitch_images(cropped_images, 1)
                    else:
                        final_image = crop_pdf_image(pdf_image)

                    yield ReportImage(report, (i + 1), final_image)

    class CondensedSection(object):
        def __init__(self, title, start_page, report_names, period):
            self.title = title
            self.start_page = start_page
            self.period = period

            self.report_names = report_names

            self.condensed_pages = None
            self.page_mappings = None
            self.report_metas = None

        def get_condensed_pages(self):
            if self.condensed_pages is None:
                self.condensed_pages = \
                    CondensedPage\
                        .generate_condensed_pages(self)

            return self.condensed_pages

        def get_page_mappings(self): 
            if self.page_mappings is None: 
                self.page_mappings = get_page_mappings(start_page=self.start_page)
            return self.page_mappings

        def get_report_metas(self): 
            if self.report_metas is None:
                self.report_metas = [
                    get_report_meta(report_name, self.period) 
                        for report_name in self.report_names ]
            return self.report_metas

        def get_report_page(self, report_name):
            for page_mapping in self.get_page_mappings():
                if report_name in page_mapping.reports:
                    return page_mapping.page

    def get_abs_path(url):
        return os.path.join(os.path.dirname(__file__), url)

    class ReportCover(object):
        def __init__(self, sections, document):
            self.sections = sections
            self.document = document

            self.pages = None
            self.pdf_file_reader = None

        def get_no_of_pages():
            return len(self.document.pages)

        def get_pdf_file_reader(self):
            if self.pdf_file_reader is None:
                temp = io.BytesIO()
                self.document.write_pdf(temp)
                temp.seek(0)

                pdf_file_reader = self.pdf_file_reader = pyPdf.PdfFileReader(temp)

            return self.pdf_file_reader

        def get_pdf_pages(self):
            if self.pages is None:
                self.pages = [
                    self.get_pdf_file_reader().getPage(i) for i in
                        range(self.get_pdf_file_reader().getNumPages()) ]

            return self.pages

        @staticmethod
        def assemble_report():
            report_cover = ReportCover.generate_report_cover()
            return bind_pdf_pages(report_cover.get_pdf_pages())

        @staticmethod
        def generate_report_cover():
            report_names = get_report_names()
            sections = [
                CondensedSection('WEEK 2019-W36', 6, report_names, 'week'),
                CondensedSection('QUARTER 2019-Q1', 13, report_names, 'quarter'),
                CondensedSection('PERIOD 2019-P01', 20, report_names, 'period'),
                CondensedSection('YEAR 2019', 27, report_names, 'year') ]

            context = {
                'sections': sections,
                'generated_on': '1/2/2019',
                'fiscal_period': '2019-W36',
                'generated_at': '12:23pm',
                'get_logo': lambda: get_base64(get_abs_path("assets/bonlogo.jpg"))}
            report_book_template = template_env.get_template(f"templates/report_book.html")
            report_book_html_content = report_book_template.render(**context)

            document = get_weasyprint_document(report_book_html_content)

            return ReportCover(sections, document)

    
    class CondensedPage(object):
        def __init__(self, section, images, page_mapping, i):
            self.images = images
            self.section = section
            self.page_mapping = page_mapping
            self.i = i

            self.pdf_file_reader = None

        def get_pdf_file_reader(self):
            if self.pdf_file_reader is None:
                self.pdf_file_reader = pyPdf.PdfFileReader(self.pdf_file)
            
            return self.pdf_file_reader

        def get_html(self):
            pdf_template = template_env\
                .get_template(f"templates/image_holders/holder-{(self.i + 1)}.html")

            context = {
                'condensed_page': self,
                'images': {
                    image.report.report_name: image
                        for image in self.images }}

            return pdf_template.render(**context)

        @staticmethod
        def generate_condensed_pages(section):
            period = section.period
            start_page = section.start_page

            images = list(ReportImage.generate_pdf_table_of_images(period=period))

        
            for period in (period and [period] or get_periods()):
                period_images = [image for image in images if image.report.period == period]

                for (i, page_mapping) in enumerate(get_page_mappings(start_page=start_page)):
                    mapping_images = [image 
                        for image in period_images 
                            if image.report.report_name in page_mapping.reports ]

                    yield CondensedPage(section, mapping_images, page_mapping, i)

