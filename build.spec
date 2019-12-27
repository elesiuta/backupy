# -*- mode: python ; coding: utf-8 -*-

import gooey
gooey_root = os.path.dirname(gooey.__file__)
gooey_languages = Tree(os.path.join(gooey_root, 'languages'), prefix = 'gooey/languages')
gooey_images = Tree(os.path.join(gooey_root, 'images'), prefix = 'gooey/images')
image_overrides = Tree('images', prefix='images')

block_cipher = None


a = Analysis(['backupy_gui.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [('u', None, 'OPTION')],
          exclude_binaries=True,
          name='BackuPy',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          windowed=True,
          icon='images/program_icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               image_overrides,
               gooey_languages,
               gooey_images,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='BackuPy')
