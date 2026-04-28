import os
import glob

def get_media_files():
    # Scan the /img directory and group by prefix or subdirectory
    if not os.path.exists('img'):
        return {}

    items = os.listdir('img')
    items = [i for i in items if not i.startswith('.')] # ignore hidden files
    
    media = {}
    valid_exts = {'jpeg', 'jpg', 'png', 'mov', 'mp4', 'webm', 'gif', 'webp'}

    for item in items:
        item_path = os.path.join('img', item)
        
        # If it's a directory, group its contents
        if os.path.isdir(item_path):
            dir_files = [df for df in os.listdir(item_path) if not df.startswith('.')]
            dir_media = []
            for df in dir_files:
                ext = df.split('.')[-1].lower()
                if ext in valid_exts:
                    dir_media.append({
                        'file': f"{item}/{df}",
                        'ext': ext,
                        'name': df
                    })
            if dir_media:
                dir_media.sort(key=lambda x: x['name'])
                for i, m in enumerate(dir_media, 1):
                    m['seq'] = i
                media[item] = dir_media

        # If it's a file, process normally by prefix
        elif os.path.isfile(item_path):
            parts = item.split('.')
            if len(parts) >= 3:
                ext = parts[-1].lower()
                try:
                    seq = int(parts[-2])
                except ValueError:
                    continue
                name = ".".join(parts[:-2])
                
                if name not in media:
                    media[name] = []
                
                media[name].append({
                    'seq': seq,
                    'file': item,
                    'ext': ext
                })
            
    # sort the prefix-based items by seq
    for name in media:
        if all('seq' in x for x in media[name]):
            media[name].sort(key=lambda x: x['seq'])
        
    return media

def generate_carousels(media):
    html = ""
    # Sort names alphabetically for consistent generation
    for name in sorted(media.keys()):
        items = media[name]
        html += '        <div class="carousel-wrapper">\n'
        html += '            <div class="carousel">\n'
        html += '                <div class="carousel-inner">\n'
        
        for idx, item in enumerate(items):
            active = ' active' if idx == 0 else ''
            filename = item['file']
            file_path = f"img/{filename}"
            ext = item['ext']
            
            html += f'                    <div class="carousel-item{active}">\n'
            if ext in ['mov', 'mp4', 'webm']:
                html += f'                        <video src="{file_path}" muted loop playsinline></video>\n'
            else:
                html += f'                        <img src="{file_path}" alt="{name} {item["seq"]}">\n'
            html += '                    </div>\n'
            
        html += '                </div>\n'
        html += '                <div class="carousel-controls">\n'
        html += '                    <button class="carousel-btn prev-btn"><svg viewBox="0 0 24 24"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg></button>\n'
        html += '                    <button class="carousel-btn next-btn"><svg viewBox="0 0 24 24"><path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg></button>\n'
        html += '                </div>\n'
        html += '            </div>\n'
        caption = name.replace("_", " ").title()
        html += f'            <div class="carousel-caption">{caption}</div>\n'
        html += '        </div>\n'
    return html

def build_page(filename, class_name, media):
    carousels_html = generate_carousels(media)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kinetic Creations</title>
    <link rel="stylesheet" href="style.css">
</head>
<body class="{class_name}">
    <header class="hero">
        <h1>Kinetic Creations</h1>
        <p>Mobiles incorporate art and movement - they add a splash of wonder to any environment.</p>
    </header>
    
    <main class="gallery-container">
{carousels_html}
    </main>

    <script src="script.js"></script>
</body>
</html>"""
    with open(filename, 'w') as f:
        f.write(html)

if __name__ == "__main__":
    media = get_media_files()
    build_page('example1.html', 'theme-dark layout-grid', media)
    build_page('example2.html', 'theme-light layout-horizontal', media)
    build_page('example3.html', 'theme-dark layout-fullscreen', media)
    print("Generated 3 example pages successfully with dynamic media mapping.")
