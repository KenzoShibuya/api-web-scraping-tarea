import requests
from bs4 import BeautifulSoup
import boto3
import uuid

def lambda_handler(event, context):
    # URL de la página del IGP de últimos sismos
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"

    # Solicitud HTTP a la página
    response = requests.get(url)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la página web del IGP'
        }

    # Parsear HTML
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar la primera tabla (la de los reportes sísmicos)
    table = soup.find('table')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla en la página web'
        }

    # Extraer los encabezados limpiando los espacios en blanco
    headers = [header.text.strip() for header in table.find_all('th')]

    rows = []
    # Extraer solo los últimos 10 sismos
    for row in table.find_all('tr')[1:11]: 
        cells = row.find_all('td')
        if cells: 
            item = {}
            for i, cell in enumerate(cells):
                header_name = headers[i] if i < len(headers) else f"columna_{i}"
                item[header_name] = cell.text.strip()
            rows.append(item)

    # Guardar en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table_db = dynamodb.Table('TablaSismos')

    # Eliminar todos los elementos previos
    scan = table_db.scan()
    with table_db.batch_writer() as batch:
        for each in scan.get('Items', []):
            batch.delete_item(
                Key={'id': each['id']}
            )

    # Insertar los 10 nuevos sismos
    for i, row in enumerate(rows):
        row['orden_historico'] = i + 1
        row['id'] = str(uuid.uuid4())
        table_db.put_item(Item=row)

    # Retorno
    return {
        'statusCode': 200,
        'body': rows
    }