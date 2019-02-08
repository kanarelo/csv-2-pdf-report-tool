import os

import base64
import jinja2
import io
import math
import pdfkit
import PyPDF2 as pyPdf
import datetime

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

ReportMeta = namedtuple('ReportMeta', ('full_report_name', 'orientation', 'short_report_name', 'detailed_caption'))
def get_report_meta(report_name, period):
    period = period if period != 'period' else 'month'

    if period == 'year':
        postfix = 'this year and last year.'
    else:
        postfix = f'this {period}, last {period} and last year same {period}.'

    return {
        'summary': ReportMeta('Summary', 'landscape', 'summary', f'Overview of the main KPIs for the current {period}.'),
        'dz_payments': ReportMeta('Sales per Delivery Region', 'landscape', 'dz_payments', f'Payments made by delivery region, separated by Web/Retail for {postfix}'),
        'dz_orders': ReportMeta('Orders per Delivery Region', 'portrait', 'dz_orders', f'Orders made by delivery region, separated by Web/Retail for {postfix}'),
        'payments': ReportMeta('Sales', 'portrait', 'payments', f'Payments made by store, {postfix}'),
        'orders': ReportMeta('Orders', 'portrait', 'orders', f'Orders made by store, {postfix}'),
        'products': ReportMeta('Products', 'portrait', 'products', f'Products sold (unit) by store, {postfix}'),
        'traffic': ReportMeta('Traffic', 'portrait', 'traffic', f'Visits by store, {postfix}'),
        'dpp': ReportMeta('Dollars Per Product', 'portrait', 'dpp', f'Payments per product sold (unit) by store, {postfix}'),
        'dpt': ReportMeta('Dollars Per Order', 'portrait', 'dpt', f'Payments per product sold (unit) by store, {postfix}'),
        'upt': ReportMeta('Products Per Order', 'portrait', 'upt', f'Payments per order by store, {postfix}'),
        'tphw': ReportMeta('Traffic Per Worked Hours', 'portrait', 'tphw', f'Visits per hour worked by store, {postfix}'),
        'sphw': ReportMeta('Sales Per Worked Hours', 'portrait', 'sphw', f'Sales per hour worked by store, {postfix}'),
        'comps': ReportMeta('Period Performance Comparison', 'portrait', 'comps', f'Period performance comparison by store, {postfix}'),
    }[report_name]

def create_report(report_name, period, index=0):
    (template_name, context) = generate_report_context(
        report_name, 
        period=period, 
        totalled_reports=get_totalled_reports(),
        comparable_reports=get_comparable_reports())

    pdf_template = utils\
        .get_jinja_template_env()\
        .get_template(f'templates/reports/{template_name}')

    if index is not None:
        context['report_index'] = (index + 1)

    report_meta = get_report_meta(report_name, period)
    context['full_report_name'] = report_meta.full_report_name
    context['detailed_caption'] = report_meta.detailed_caption
    context['orientation'] = report_meta.orientation

    return pdf_template.render(**context)

class ReportBooklet(object):
    def __init__(self, title, report_names, period):
        self.title = title
        self.period = period

        self.report_names = report_names
        self.report_metas = None

    def create_report(self, report_name, index):
        return create_report(report_name, self.period, index=index)

    def get_report_metas(self): 
        if self.report_metas is None:
            self.report_metas = [
                get_report_meta(report_name, self.period) 
                    for report_name in self.report_names ]

        return self.report_metas

    def get_content(self):
        return "\n".join([
            self.create_report(report_name, i)
                for (i, report_name) in enumerate(self.report_names)])

get_quarter = lambda d: math.ceil(d.month/3.0)
class ReportBook(object):
    def __init__(self, document):
        self.document = document

    def get_no_of_pages():
        return len(self.document.pages)

    @staticmethod
    def assemble_report_book():
        report_book = ReportBook.generate_report_book()
        report_book.document.write_pdf(
            datetime.datetime.now().strftime('final_reports/BLSR_BOOK_%Y-%m-%d.pdf'))

    @staticmethod
    def assemble_report_booklets(date=None, period=None):
        date = date or datetime.datetime.now()

        for period in (period and [period] or get_periods()):
            report_book = ReportBook.generate_report_book(date=date, period=period)
            if period == 'week':
                period_stamp = '%Y-W%U'
            elif period == 'quarter':
                period_stamp = f'%Y-Q{get_quarter(date)}'
            elif period == 'period':
                period_stamp = '%Y-P%m'
            elif period == 'year':
                period_stamp = '%Y-FY'

            report_book.document.write_pdf(date.strftime(
                f'final_reports/BLSR_{period_stamp}_%Y-%m-%d.pdf'))

    @staticmethod
    def generate_report_book(date=None, period=None):
        report_names = get_report_names()
        booklets = []

        if date is None:
            date = datetime.datetime.now()

        if period is None:
            booklets += [
                ReportBooklet(date.strftime('WEEK %Y-W%U'), report_names, 'week'),
                ReportBooklet(date.strftime(f'QUARTER %Y-Q{get_quarter(date)}'), report_names, 'quarter'),
                ReportBooklet(date.strftime('PERIOD %Y-P%m'), report_names, 'period'),
                ReportBooklet(date.strftime('YEAR %Y'), report_names, 'year')]
        elif period == 'week':
            booklets.append(
                ReportBooklet(date.strftime('WEEK %Y-W%U'), report_names, 'week'))
        elif period == 'quarter':
            booklets.append(
                ReportBooklet(date.strftime(f'QUARTER %Y-Q{get_quarter(date)}'), report_names, 'quarter'))
        elif period == 'period':
            booklets.append(
                ReportBooklet(date.strftime('PERIOD %Y-P%m'), report_names, 'period'))
        elif period == 'year':
            booklets.append(
                ReportBooklet(date.strftime('YEAR %Y'), report_names, 'year'))

        context = {
            'booklets': booklets,
            'period_pct_complete': '56%',
            'generated_on': date.strftime('%d/%m/%Y'),
            'fiscal_period': date.strftime('%Y-W%U'),
            'generated_at': date.strftime('%I:%M%p'),
            'get_logo': lambda: get_base64(get_abs_path("assets/bonlogo.jpg"))}
        report_book_template = utils\
            .get_jinja_template_env()\
            .get_template(f"templates/report_book.html")
        report_book_html_content = report_book_template.render(**context)

        comps_report_html = create_report('comps', period, index=12)
        report_book_html_content = f'{report_book_html_content}\n{comps_report_html}'

        document = get_weasyprint_document(report_book_html_content)
        return ReportBook(document)

def get_weasyprint_document(html_content):
    font_config = weasyprint.fonts.FontConfiguration()
    return weasyprint\
        .HTML(string=html_content)\
        .render(
            stylesheets=[weasyprint.CSS(string=utils.get_css())], 
            font_config=font_config)

def get_base64(image, image_format='png', as_string=True):
    if type(image) == str:
        image = PILImage.open(image)
    
    with io.BytesIO() as temp:
        image.save(temp, image_format.upper(), resolution=80)
        temp.seek(0)

        if as_string:
            return f"data:image/{image_format};base64,{base64.b64encode(temp.read()).decode('utf-8')}"

        return temp

<<<<<<< HEAD
def get_abs_path(url):
    return os.path.join(os.path.dirname(__file__), url)

def generate_report_book():
    ReportBook.assemble_report_book()
=======
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

>>>>>>> 33e57548532c3633be6c733a86df8efb1f777b92
