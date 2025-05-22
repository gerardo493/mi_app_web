from weasyprint import HTML
HTML(string='<h1>Hola PDF</h1>').write_pdf('test.pdf')