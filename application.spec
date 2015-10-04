# -*- mode: python -*-
a = Analysis(['application.py'],
             pathex=['/Users/XYK/Desktop/Dropbox/Choxue-scoreboard-OCR'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
a.datas += [('athlete_data.csv','athlete_data.csv','DATA')]
a.datas += [('tpe_gym_test.jpg','tpe_gym_test.jpg','DATA')]
a.datas += [('ssocr','ssocr','DATA')]
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='application',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='application')
