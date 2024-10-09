from ebooklib import epub
from bs4 import BeautifulSoup
import re
import json
import os

# ePub dosyasını oku
file_path = '/Users/gucluceyhan/Documents/Güçlü Kişisel/dusuncetarihi_Orhan_Hancerlioglu.epub'

if not os.path.exists(file_path):
    raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")

book = epub.read_epub(file_path)

# Metni çıkarma (sadece ilk 10 sayfa) İçindekiler kısmını bulmak için
all_text = []
page_limit = 10
current_page = 0

for item in book.get_items():
    if item.media_type == 'application/xhtml+xml':  # Belgeleri belirlemek için
        if current_page < page_limit:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')
            all_text.append(soup.get_text())
            current_page += 1
        else:
            break  # İlk 10 sayfadan sonrasını tarama

# Tüm metni birleştir
full_text = "\n\n".join(all_text)

# İçindekiler kısmını bulma ve dizin kısmına kadar her şeyi alma
def extract_table_of_contents(text):
    toc_start = None
    toc_end = None
    lines = text.split("\n")

    # İçindekiler ve dizin bölümlerini bulma
    for idx, line in enumerate(lines):
        # Daha esnek bir kelime arama ile "İçindekiler" ve "Dizin" bölümlerini bulalım
        if re.search(r'(?i)İçindekiler', line):  # 'İçindekiler' kelimesini büyük/küçük harf farketmeksizin ara
            toc_start = idx
        elif re.search(r'(?i)Dizin', line):  # 'Dizin' kelimesini büyük/küçük harf farketmeksizin ara
            toc_end = idx
            break
    
    if toc_start is not None and toc_end is not None:
        return lines[toc_start:toc_end]
    elif toc_start is not None:
        return lines[toc_start:]
    else:
        print("Uyarı: İçindekiler veya Dizin bölümü bulunamadı.")
        return []

# İçindekiler kısmını çıkar
toc_lines = extract_table_of_contents(full_text)

# Başlıkları ve rakamları ayırma
headings_with_numbers = []
headings_without_numbers = []
loose_numbers = []

for line in toc_lines:
    line = line.strip()
    # Eğer satırda bir rakam varsa bunu başlık ve sayfa numarası olarak al
    if re.search(r'^\d+$', line):  # Sadece sayı içeren satırları bul
        loose_numbers.append(line)
    elif re.search(r'^(\d+)\s+(.+)$', line):  # Satırda önce sayı sonra başlık olup olmadığını kontrol et
        match = re.match(r'^(\d+)\s+(.+)$', line)
        if match:
            page_number = match.group(1).strip()
            title = match.group(2).strip()
            headings_with_numbers.append((title, page_number))
    elif re.search(r'\d+$', line):  # Satırda sayfa numarası olup olmadığını kontrol et
        match = re.match(r'(.+?)\s+(\d+)$', line)
        if match:
            title = match.group(1).strip()
            page_number = match.group(2).strip()
            headings_with_numbers.append((title, page_number))
    else:
        headings_without_numbers.append(line)

# Sayfa numarasız başlıkları sayfa numaralarıyla ilişkilendirme
def match_headings_with_numbers(loose_numbers, headings_without_numbers, headings_with_numbers):
    matched_headings = []
    number_index = 0

    # Önce başlıksız sayılarla başlıkları eşleştir
    for heading in headings_without_numbers:
        if number_index < len(loose_numbers):
            matched_headings.append((heading, loose_numbers[number_index]))
            number_index += 1
        else:
            matched_headings.append((heading, None))

    # Sonra sayfa numarası olan başlıkları ekle
    matched_headings.extend(headings_with_numbers)
    
    return matched_headings

# Sayfa numarasız başlıkları sayfa numaralı başlıklarla eşleştir
final_headings = match_headings_with_numbers(loose_numbers, headings_without_numbers, headings_with_numbers)

# Ayırdığımız başlık ve sayfa numaralarını alt alta yazdırma
print("Başlıklar ve Sayfa Numaraları:")
for title, page in final_headings:
    print(f"Başlık: {title}, Sayfa: {page if page else 'Boş'}")

# Tüm metni çıkarma (kitabın tamamı)
all_text = []
for item in book.get_items():
    if item.media_type == 'application/xhtml+xml':
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        all_text.append(soup.get_text())

# Tüm metni birleştir
full_text = "\n\n".join(all_text)

# Sayfalara göre metni bölme
pages = re.split(r'\n\nSayfa\s+\d+', full_text)  # Sayfa numarası metin içeriği şeklinde bölüyoruz

# Her başlığın başladığı sayfa ile bir sonraki başlığa kadar olan içeriği bulma
def extract_section_by_page(headings, pages):
    dataset = []
    
    for i, (title, start_page) in enumerate(headings):
        if start_page is None:
            continue

        # Başlangıç sayfasını buluyoruz
        start_page = int(start_page)
        if start_page < len(pages):
            start_content = pages[start_page]
        else:
            continue  # Eğer sayfa numarası yanlışsa, atlıyoruz
        
        # Bir sonraki başlığa kadar olan bölüü almak için
        if i + 1 < len(headings) and headings[i + 1][1] is not None:
            end_page = int(headings[i + 1][1])
            if end_page < len(pages):
                completion = "\n\n".join(pages[start_page:end_page])
            else:
                completion = "\n\n".join(pages[start_page:])  # Son başlıksa sonuna kadar al
        else:
            completion = "\n\n".join(pages[start_page:])  # Son başlıksa sonuna kadar al

        dataset.append({
            "prompt": title,
            "completion": completion.strip()
        })
    
    return dataset

# İçindekiler kısmındaki başlıklar için ilgili bölümleri çıkarıyoruz
dataset = extract_section_by_page(final_headings, pages)

# JSON veri setini kaydetme
with open('/Users/gucluceyhan/Downloads/final_prompt_completion_dataset.json', 'w', encoding='utf-8') as f:
    for entry in dataset:
        json.dump(entry, f, ensure_ascii=False)
        f.write('\n')

print("Veri seti kaydedildi.")