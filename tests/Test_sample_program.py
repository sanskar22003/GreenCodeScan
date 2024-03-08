from sample_program import Student

def test_welcome():
    x = Student("Mike", "Olsen", 2019)
    assert x.firstname == "Mike"
    assert x.lastname == "Olsen"
    assert x.graduationyear == 2019
    expected_output = "Welcome Mike Olsen to the class of 2019\n"
    assert_output(capsys, x.welcome, expected_output)

def assert_output(capsys, func, expected_output):
    captured = capsys.readouterr()
    func()
    assert captured.out == expected_output
