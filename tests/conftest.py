import os
pj = os.path.join

TEST_DIR = 'toml-test/tests'

def get_tomltest_cases(rootdir):
    expect_dirs = ['invalid', 'invalid-encoder', 'valid']
    realdir = pj(rootdir, TEST_DIR)
    dirs = sorted(os.listdir(realdir))
    assert all(i in dirs for i in expect_dirs)
    rv = {}
    for d in expect_dirs:
        rv[d] = {}
        files = os.listdir(pj(realdir, d))
        for f in files:
            bn, ext = f.rsplit('.', 1)
            if bn not in rv[d]:
                rv[d][bn] = {}
            with open(pj(realdir, d, f)) as inp:
                rv[d][bn][ext] = inp.read()
    return rv

def pytest_generate_tests(metafunc):
    rootdir = metafunc.config.rootdir
    test_list = get_tomltest_cases(rootdir)
    if 'valid_case' in metafunc.fixturenames:
        metafunc.parametrize('valid_case', test_list['valid'].values(),
                             ids=list(test_list['valid'].keys()))
    elif 'invalid_decode_case' in metafunc.fixturenames:
        metafunc.parametrize('invalid_decode_case',
                             test_list['invalid'].values(),
                             ids=list(test_list['invalid'].keys()))
    elif 'invalid_encode_case' in metafunc.fixturenames:
        metafunc.parametrize('invalid_encode_case',
                             test_list['invalid-encoder'].values(),
                             ids=list(test_list['invalid-encoder'].keys()))
