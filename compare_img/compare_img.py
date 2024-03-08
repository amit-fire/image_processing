from PIL import Image
import imagehash
import imageio
import os
import sys
import shutil
import subprocess
import random
import json
import argparse

def aaa():
    print("Hello World!")
    parser1 = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')

    parser = argparse.ArgumentParser()

    parser.add_argument('filename') 
       
   # parser.add_argument('-h', '--help')

    args = parser.parse_args()
    print(args)
    #print(args.filename, args.count, args.verbose) 

def help_msg():
    print('Usage: python ' + os.path.basename(__file__) + ' <json_file>\nhelp:  python ' + os.path.basename(__file__) + ' -h|--help')

def parse_input(input_file):
    f = open(input_file) 
    data = json.load(f)
    f.close()
    return data

def collect_parameters(parameters_file):
    f = open(parameters_file, 'r')
    lines = f.readlines()
    f.close()
    params = {}
    for line in lines:
        splitLine = line.split('=')
        values = splitLine[1].split(',')
        values[-1] = values[-1].strip()
        params[splitLine[0]] = values
    return params

def select_parameters(parameters):
    res={}
    cmd = ''
    for k,v in parameters.items():
        val = random.choice(v)
        if val != 'no':
            res[k]=val
            cmd += '--' + k + ' ' + val + ' '
    #print('args',res)
    return cmd

def execute(data):
    generate_diff = False
    if 'generate_diff' in data and data['generate_diff']:
        generate_diff = True

    if 'scenarios' in data and len(data['scenarios']) > 0:
        return test_determined(data['test_dir'], data['scenarios'], data['program_path'], generate_diff)
    elif os.path.isfile(data['parameters_file']):
        parameters = collect_parameters(data['parameters_file'])
        if 'different_parameters_every_build' in data and data['different_parameters_every_build']:
            return test_different_parameters(data['test_dir'], data['number_of_tests'], data['versions_per_test'], parameters, data['program_path'], generate_diff)
        else:
            return test_same_parameters(data['test_dir'], data['number_of_tests'], data['versions_per_test'], parameters, data['program_path'], generate_diff)

def test_determined(test_dir, scenarios, program_path, generate_diff):
    res = {}

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    for scenario in scenarios:
        file_name = os.path.basename(scenario).split('.')[0]
        f = open(scenario, 'r')
        lines = f.readlines()
        f.close()
        
        run_res=run_determined(os.path.join(test_dir, file_name), lines, program_path, generate_diff)
        res[file_name]=run_res     
        print('test ' + file_name + ' does not match ' + str(len(run_res['no_match'])) + ' match ' + str(len(run_res['match'])))
        print('does not match', run_res['no_match'])
        print('match', run_res['match'])

    print('results for all tests', res)
    return res

def run_determined(test_dir, lines, program_path, generate_diff):
    i = 0
    out_dir = os.path.join(test_dir, 'out')
    os.makedirs(out_dir)

    res = {'match': [], 'no_match': []}

    for line in lines:
        png = os.path.join(test_dir, str(i) + '.png')
        cmd = 'node ' + program_path + ' ' + line.strip() + ' --build ' + str(i) + ' ' + png
        print(cmd)
        os.system(cmd)

        if i == 0:
            #print(f'build 0 {png}')
            img0 = Image.open(png)
            hash0 = imagehash.phash(img0)

        if i > 0:
            out = os.path.join(out_dir, str(i)+'.png')
            #print(out)
            compare_and_report(img0, hash0, generate_diff, png, out, res)           

        i+=1
    return res

def test_same_parameters(test_dir, number_of_tests, versions_per_test, parameters, program_path, generate_diff):
    res = {}

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    i=0
    while i < number_of_tests:
        selected_parameters = select_parameters(parameters)
        test = 'test-' + str(i+1)
        run_res = run_same_parameters(os.path.join(test_dir, test), versions_per_test, program_path, selected_parameters, generate_diff)
        res[test]=run_res     
        print('test ' + test + ' does not match ' + str(len(run_res['no_match'])) + ' match ' + str(len(run_res['match'])))
        print('does not match', run_res['no_match'])
        print('match', run_res['match'])
        i+=1
    print('results for all tests', res)
    return res

def run_same_parameters(test_dir, versions_per_test, program_path, parameters, generate_diff):
    out_dir = os.path.join(test_dir, 'out')
    os.makedirs(out_dir)

    res = {'match': [], 'no_match': []}
    i = 0
    while i <= versions_per_test:
        png = os.path.join(test_dir, str(i) + '.png')
        cmd = 'node ' + program_path + ' ' + parameters + '--build ' + str(i) + ' ' + png
        print(cmd)
        os.system(cmd)

        if i == 0:
            #print(f'build 0 {png}')
            img0 = Image.open(png)
            hash0 = imagehash.phash(img0)

        if i > 0:
            out = os.path.join(out_dir, str(i) + '.png')
            #print(out)
            compare_and_report(img0, hash0, generate_diff, png, out, res)           

        i+=1
    return res

def test_different_parameters(test_dir, number_of_tests, versions_per_test, program_path, parameters, generate_diff):
    res = {}

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    i=1
    while i <= number_of_tests:
        test = 'test-' + str(i)
        run_res = run_different_parameters(os.path.join(test_dir, test), versions_per_test, program_path, parameters, generate_diff)
        res[test]=run_res     
        print('test ' + test + ' does not match ' + str(len(run_res['no_match'])) + ' match ' + str(len(run_res['match'])))
        print('does not match', run_res['no_match'])
        print('match', run_res['match'])
        i+=1
    print('results for all tests', res)
    return res

def run_different_parameters(test_dir, versions_per_test, parameters, program_path, generate_diff):
    i = 0

    out_dir = os.path.join(test_dir, 'out')
    os.makedirs(out_dir)

    res = {'match': [], 'no_match': []}
    while i < versions_per_test:
        selected_parameters = select_parameters(parameters)
        png = os.path.join(test_dir, str(i) + '.png')
        cmd = 'node ' + program_path + ' ' + selected_parameters + '--build ' + str(i) + ' ' + png
        print(cmd)
        os.system(cmd)

        if i == 0:
            #print(f'build 0 {png}')
            img0 = Image.open(png)
            hash0 = imagehash.phash(img0)

        if i > 0:
            out = os.path.join(out_dir, str(i)+'.png')
            #print(out)
            compare_and_report(img0, hash0, generate_diff, png, out, res)           

        i+=1
    return res

def compare_and_report(img1, hash1, generate_diff, build_x, output_path, res):
    #print('build x', build_x)

    # load image
    img2 = Image.open(build_x)
    # perceptual hash
    hash2 = imagehash.phash(img2)

    # compare hashes
    similarity = 1 - (hash1 - hash2) / max(len(hash1.hash) * 8, 1)

    if similarity < 0.99:
        if generate_diff:
            diff_img = Image.new('RGB', img1.size)
            for x in range(img1.width):
                for y in range(img1.height):
                    if img1.getpixel((x, y)) != img2.getpixel((x, y)):
                        diff_img.putpixel((x, y), (255, 0, 0))  # differences appear in red
            diff_img.save(output_path)
            print(f"files don't match. output {output_path}")
        no_match = res['no_match']
        no_match.append(build_x)
    else:
        print('files match')
        match = res['match']
        match.append(build_x)

def generate_report(results, test_dir):
    report_file = os.path.join(test_dir, 'report.html')
    print('generating report. ' + report_file)
    content = '<html>\n\t<body>'
    no_match = '\n\t\t<div>does not match</div>\n\t\t</br>'
    match = '\n\t\t<div>match</div>\n\t\t</br>'
    no_match_sections = ''
    match_sections = ''
    total_no_match = 0
    total_match = 0
    for result in results:
        scenario = result + ' (does not match: ' + str(len(results[result]['no_match'])) + ', match: ' + str(len(results[result]['match'])) + ')'

        link = '\n\t\t<a href="#' + result + '">' + scenario + '</a>\n\t\t</br>\n\t\t</br>'
        section = '\n\t\t<section id="' + result + '">\n\t\t\t<div><u>' + scenario + '</u></div>\n\t\t\t<div>does not match</div>'
        
        total_no_match += len(results[result]['no_match'])
        total_match += len(results[result]['match'])

        if len(results[result]['no_match']) == 0:
            section += '\n\t\t\t<div>all tests match</div>'
        else:
            for test in results[result]['no_match']:
                section += '\n\t\t\t<div>' + test + '</div>'
        section += '\n\t\t\t<div>match</div>'
        if len(results[result]['match']) == 0:
            section += '\n\t\t\t<div>all tests does not match</div>'
        else:
            for test in results[result]['match']:
                section += '\n\t\t\t<div>' + test + '</div>'

        section += '\n\t\t</section>\n\t\t</br>'
        if len(results[result]['no_match']) > 0:
            no_match += link
            no_match_sections += section
        else:
            match += link
            match_sections += section

    if total_no_match > 0:
        match += '\n\t\t<div>all scenarios have at least one does not match test</div>'
    if total_no_match == 0:
        no_match += '\n\t\t<div>all tests match</div>'

    html = content + no_match + match + '\n\t\t</br>\n\t\t<hr>\n\t\t</br>' + no_match_sections + match_sections + '\n\t</body>\n</html>'
    f = open(report_file, 'w')
    f.write(html)
    f.close()

def main():
    parser = argparse.ArgumentParser(description='1. execute 2. compare 3. generate diff (if relevant) 4. generate report')
    parser.add_argument('config_file', nargs='?', help='config file')
    args = parser.parse_args()

    if args.config_file:
        data = parse_input(sys.argv[1])
        #print(data)
        results = execute(data)
        generate_report(results, data['test_dir'])
    else:
        print('config file was not provided. -h/--help for details')
        
if __name__ == '__main__':
    main()