import subprocess 

commands = [
    'ssocr gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 tpe_gym_test.jpg -D -d -1',
    'ssocr gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 tpe_gym_test.jpg -D -d -1',
    'ssocr gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 tpe_gym_test.jpg -D -d -1',
    'ssocr gray_stretch 190 254 invert remove_isolated crop 307 500 55 73 tpe_gym_test.jpg -D -d -1',
    'ssocr gray_stretch 190 254 invert remove_isolated crop 307 150 55 73 tpe_gym_test.jpg -D -d -1'
]
# run in parallel
processes = [subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True) for cmd in commands]
# do other things here..
# wait for completion
for x in processes:
	print x.stdout.read()
