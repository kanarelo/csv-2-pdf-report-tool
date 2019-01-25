
from flask import Flask, render_template, request, make_response

from reports import generate_report_context
from pdf_utils import generate_pdf_reportbook, generate_condensed_pdf

app = Flask(__name__)

@app.route('/static/<path:path>')
def static_file(path):
    return app.send_static_file(path)

@app.route("/report/<report_name>")
def report(report_name=None):
    file_type = 'html'

    if '.pdf' in report_name:
        (report_name, file_type) = report_name.split('.')

    period = None
    if request.args.get('period') is not None:
        period = request.args.get('period')
    
    if file_type == 'html':
        (template_name, context) = generate_report_context(report_name, period=period)
        return render_template(template_name, **context)
    elif file_type == 'pdf':
        if report_name == "comprehensive_report":
            generate_report_name = None
        else:
            generate_report_name = report_name

        binary_pdf = generate_condensed_pdf(period=period, close_files=True)
        response = make_response(binary_pdf)

        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=%s.pdf' % report_name

        return response
    else:
        return None

if __name__ == "__main__":
    app.run()
