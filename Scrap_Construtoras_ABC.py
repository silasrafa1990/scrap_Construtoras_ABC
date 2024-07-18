import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configurações para exibir o DataFrame completo
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

def scrap_mbigucci():
    url = 'https://www.mbigucci.com.br/mb/busca?quero=10&cidade=&bairro=&tipo=&valor=&status='
    data_item = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/91.0.4472.124 Safari/537.36'}

    # Fazendo a solicitação HTTP
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        all_items = soup.find_all('div', class_='empreendimento')

        for item in all_items:
            city = item.find('p', class_='cidade').text.strip()
            neighborhood = item.find('p', class_='bairro').text.strip()
            status_details = item.find('div', class_='status').text.strip()
            dorms = item.find('p', class_='dorm').text.strip()

            # Remover espaços em branco da coluna "Quartos"
            dorms = re.sub(r'\s+', ' ', dorms)

            area = item.find('p', class_='area').text.strip()

            row = {'Bairro_Cidade ': city, 'Bairro': neighborhood, 'Status': status_details, 'Quartos': dorms, 'Area': area}
            data_item.append(row)

        df = pd.DataFrame(data_item)
        df['Construtora'] = 'MBigucci'
        return df

def scrap_patriani():
    url = 'https://www.construtorapatriani.com.br/imoveis'
    data_item = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/91.0.4472.124 Safari/537.36'}

    # Fazendo a solicitação HTTP
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        all_itens = soup.find_all('div', class_='styles__Wrapper-sc-oxt5ey-4 kzFlri transition-200')

        for item in all_itens:
            address = item.find('span', class_='styles__Wrapper-sc-k2s963-0 cezBsh tag size-md weight-400').text
            item_details = item.find('ul', class_='styles__Details-sc-oxt5ey-3 dKrrci').text
            status_details = item.find('span', class_="styles__Wrapper-sc-k2s963-0 cezBsh tag size-sm weight-500").text
            row = {'Bairro_Cidade ': address, 'Dados': item_details, 'Status': status_details}
            data_item.append(row)

        df = pd.DataFrame(data_item)

        def extract_details(row):
            details = row['Dados']

            valor_m2 = re.search(r'(\d+\s*[e,]?\s*\d*)\s*m²', details)
            num_vagas = re.search(r'(\d+)\s*vagas?', details)

            # Atualização na expressão regular para suítes e dormitórios
            suites_dorms_match = re.search(r'(\d+)\s*(suíte|dorm)[^\d]*(\d*)', details, re.IGNORECASE)

            if suites_dorms_match:
                num_suites = f"{suites_dorms_match.group(1)} suítes" if suites_dorms_match.group(2).lower() == 'suíte' else None
                num_dorms = f"{suites_dorms_match.group(1)} dorms" if suites_dorms_match.group(2).lower() == 'dorm' else None
            else:
                num_suites = num_dorms = None

            entrega = re.search(r'Entreg(?:a|ue)\s*([^\d]+[\d\s*\/]+)', details)

            valor_m2 = valor_m2.group(1) if valor_m2 else None
            num_vagas = num_vagas.group(1) if num_vagas else None
            entrega = entrega.group(1).strip() if entrega else None

            return {
                'Valor_m2': valor_m2,
                'Num_Vagas': num_vagas,
                'Num_Suites': num_suites,
                'Num_Dorms': num_dorms,
                'Entrega': entrega
            }

        # Aplicar a função para criar novas colunas
        df = pd.concat([df, df.apply(extract_details, axis=1, result_type='expand')], axis=1)

        # Adicionar a coluna 'Num_Dorms_Suites' que é a junção das colunas 'Num_Dorms' e 'Num_Suites'
        df['Num_Dorms_Suites'] = df['Num_Dorms'].astype(str) + ' ' + df['Num_Suites'].astype(str)

        # Reorganizar as colunas na ordem desejada
        df = df[['Bairro_Cidade ', 'Valor_m2', 'Num_Dorms', 'Num_Dorms_Suites', 'Entrega', 'Status', 'Dados']]

        # Substituir valores None por NaN para consistência
        df = df.replace('None', pd.NA)
        df['Construtora'] = 'Patriani'
        return df

def scrap_paddan():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    data_items = []

    url = 'https://paddan.com.br/empreendimentos'
    driver.get(url)

    # Espera explícita para aguardar o carregamento da página
    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'row')))

    # Ação de rolagem para baixo algumas vezes para carregar mais produtos
    for _ in range(10):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        driver.implicitly_wait(2)

    # Agora, esperamos até que os elementos 'column-block' estejam presentes no DOM
    items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'column-block')))

    for item in items:
        status = item.find_element(By.CLASS_NAME, 'tipo').text
        name = item.find_element(By.TAG_NAME, 'h4').text
        span = item.find_element(By.TAG_NAME, 'span').text.strip()

        # Aqui adicionamos a extração do texto da tag <p> dentro da tag <figcaption>
        descricao_parts = item.find_element(By.TAG_NAME, 'figcaption').find_elements(By.TAG_NAME, 'p')
        bairro_cidade = descricao_parts[1].text.strip()
        bairro_cidade = re.sub(r'\n','',bairro_cidade)

        data_items.append({
            'Status': status,
            'Título': name,
            'Quartos': span,
            'Bairro_Cidade': bairro_cidade
        })

    df = pd.DataFrame(data_items)
    df['Construtora'] = 'Paddan'
    return df

def scrap_mzm():
    url = 'https://mzm.com.br/imoveis/'
    data_item = []

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/91.0.4472.124 Safari/537.36'}

    # Fazendo a solicitação HTTP
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        all_items = soup.find_all('div', class_='box-imovel')

        for item in all_items:
            city = item.find('p', class_="cid-est").text.strip()
            status_details = item.find('div', class_='img-status').text.strip()

            # Aqui, selecionamos todas as tags <p> dentro da descrição
            details_tags = item.find('div', class_='descricao').find_all('p')

            # Concatenamos todos os textos das tags <p>
            details_text = ' '.join(tag.get_text(strip=True) for tag in details_tags)

            # Usamos regex para extrair os intervalos de "m²"
            matches = re.findall(r'(\d+\s*[a-zA-Z]*\s*-?\s*\d*\s*[a-zA-Z]*)', details_text)
            details = ', '.join(matches) if matches else ''

            # Removemos os intervalos da string original
            details_text = re.sub(r'\d+\s*[a-zA-Z]*\s*-?\s*\d*\s*[a-zA-Z]*', '', details_text).strip()

            # Modificação: Dividimos os detalhes pela vírgula e atribuímos a campos separados
            details_list = details.split(', ')

            row = {'Bairro_Cidade ': city, 'Status': status_details,
                   'Metragem': details_list[0] if len(details_list) > 0 else '',
                   'Quartos': details_list[1] if len(details_list) > 1 else '',
                   'Vagas': details_list[2:5] if len(details_list) > 2 else 'None'}

            data_item.append(row)

        df = pd.DataFrame(data_item)
        df['Construtora'] = 'MZM'
        return df

def scrap_maximo_aldana():
    url = 'https://maximoaldana.com.br/imoveis/'
    data_item = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/91.0.4472.124 Safari/537.36'}


    response = requests.get(url, headers=headers)

    soup = BeautifulSoup(response.content, 'html.parser')

    all_items_data = soup.find_all('div', class_='item-body flex-grow-1')
    for item in all_items_data:
        address = item.find('address').text.strip()
        local = item.find('li', class_="h-local").text.strip()

        dorms_tag = item.find('li', class_="h-beds")
        dorms = dorms_tag.find('span', class_='item-amenities-text').find_next('span').text.strip() if dorms_tag else "N/A"

        garage_tag = item.find('li', class_="h-cars")
        garage = garage_tag.find('span', class_='item-amenities-text').find_next('span').text.strip() if garage_tag else "N/A"

        area_tag = item.find('li', class_="h-area")
        area = area_tag.find('i', class_='houzez-icon icon-ruler-triangle mr-1').find_next('span').text.strip() if area_tag else "N/A"

            # Agora procure a tag de status dentro de 'item'
        status_tag = item.find('a', class_='label-status')
        status_text = status_tag.text.strip() if status_tag else "N/A"

        row = {'Status': status_text,
                   'Endereço': address,
                   'Bairro_Cidade': local,
                   'Quartos': dorms,
                   'Area': area,
                   'Garagem': garage}

        data_item.append(row)

    df = pd.DataFrame(data_item)
    df['Construtora'] = 'Maximo Aldana'
    return df

# Criação da lista de DataFrames
dfs = [scrap_maximo_aldana(), scrap_mbigucci(), scrap_patriani(), scrap_paddan(), scrap_mzm()]

# Concatenação dos DataFrames
result_df = pd.concat(dfs, ignore_index=True)

# Exibir o DataFrame resultante
print(result_df)

# Salvar em um arquivo CSV
result_df.to_csv('dados_completos.csv', index=False)
