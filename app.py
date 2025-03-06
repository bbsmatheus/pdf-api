import sys
import os
# Força o Pyppeteer a usar a revisão 818858 (tente também outras, se necessário)
os.environ["PYPPETEER_CHROMIUM_REVISION"] = "818858"

import asyncio
import logging
from flask import Flask, request, send_file, jsonify
import nest_asyncio
from pyppeteer import launch
from io import BytesIO

# Configura o event loop para Windows usando o Selector
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

nest_asyncio.apply()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

async def generate_pdf(url, output_pdf='output.pdf'):
    try:
        logging.debug("Tentando iniciar o navegador...")
        # Não especificamos 'executablePath' para que o Pyppeteer baixe o Chromium com a revisão indicada.
        browser = await launch(
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--force-device-scale-factor=1'  # força o scale do dispositivo para 1
            ],
            headless=True
        )
        logging.debug("Navegador iniciado com sucesso.")
    except Exception as e:
        logging.error("Erro ao iniciar o navegador: " + str(e))
        raise e

    page = await browser.newPage()
    # Define o viewport conforme o código do Colab
    await page.setViewport({
        'width': 1366,
        'height': 1080,
        'deviceScaleFactor': 1
    })

    try:
        logging.debug(f"Carregando a URL: {url}")
        await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 60000})
    except Exception as e:
        logging.error("Erro ao carregar a URL: " + str(e))
        await browser.close()
        raise e

    try:
        logging.debug("Adicionando style tag para impressão...")
        await page.addStyleTag({
            'content': '@media print { a[href]:after { content: "" !important; } }'
        })
    except Exception as e:
        logging.error("Erro ao adicionar style tag: " + str(e))

    try:
        logging.debug("Gerando o PDF...")
        await page.pdf({
            'path': output_pdf,
            'format': 'A4',
            'printBackground': True,
            'margin': {
                'top': '10mm',
                'right': '10mm',
                'bottom': '10mm',
                'left': '10mm'
            },
            'scale': 0.8,  # Igual ao que você usa no Colab
            'preferCSSPageSize': True
        })
        logging.debug("PDF gerado com sucesso.")
    except Exception as e:
        logging.error("Erro ao gerar o PDF: " + str(e))
        await browser.close()
        raise e

    await browser.close()

@app.route('/convert', methods=['GET', 'POST'])
def convert():
    url = request.args.get('url') or request.form.get('url')
    if not url:
        return jsonify({"erro": "URL não fornecida"}), 400

    output_pdf = 'output.pdf'
    try:
        logging.debug("Iniciando a conversão da URL para PDF...")
        asyncio.get_event_loop().run_until_complete(generate_pdf(url, output_pdf))
        
        logging.debug("Carregando o PDF em memória...")
        with open(output_pdf, 'rb') as f:
            pdf_data = f.read()
        os.remove(output_pdf)
        
        pdf_io = BytesIO(pdf_data)
        pdf_io.seek(0)
        logging.debug("Enviando o arquivo PDF gerado para o usuário.")
        return send_file(pdf_io,
                         as_attachment=True,
                         download_name='arquivo.pdf',
                         mimetype='application/pdf')
    except Exception as e:
        logging.error("Erro na conversão: " + str(e))
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False, threaded=False)

