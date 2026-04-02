from pathlib import Path

repl = {
    'use_container_width=True': 'width="container"',
    'use_container_width=False': 'width=0',
}

changed_files = []

for path in Path('frontend').rglob('*.py'):
    text = path.read_text(encoding='utf-8')
    new = text
    for old, new_val in repl.items():
        new = new.replace(old, new_val)
    if new != text:
        path.write_text(new, encoding='utf-8')
        changed_files.append(str(path))

print('Changed', len(changed_files), 'files')
for f in changed_files:
    print('-', f)
