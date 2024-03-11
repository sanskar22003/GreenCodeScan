from sample_program_two import Car, Boat, Plane

def test_move(capsys):
    car1 = Car("Ford", "Mustang")
    boat1 = Boat("Ibiza", "Touring 20")
    plane1 = Plane("Boeing", "747")
    
    expected_outputs = [
        "Drive!\n",
        "Sail!\n",
        "Fly!\n"
    ]
    
    assert_output(capsys, car1.move, expected_outputs[0])
    assert_output(capsys, boat1.move, expected_outputs[1])
    assert_output(capsys, plane1.move, expected_outputs[2])

def assert_output(capsys, func, expected_output):
    func()
    captured = capsys.readouterr()
    assert captured.out == expected_output
