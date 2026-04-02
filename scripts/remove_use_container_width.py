from pathlib import Path

def convert_line(line):
    return line.replace('use_container_width=True', 'width="container"').replace('use_container_width=False', 'width=0')

updated = []
for path in Path('frontend').rglob('*.py'):
    text = path.read_text('utf-8')
    if 'use_container_width' in text:
        new = convert_line(text)
        if new != text:
            path.write_text(new, 'utf-8')
            updated.append(path)
print('Updated', len(updated), 'files')
for p in updated:
    print(p)
