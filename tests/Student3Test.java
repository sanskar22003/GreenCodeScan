import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class Student3Test {
    @Test
    void testDisplay() {
        Student3 s1 = new Student3();
        s1.id = 1;
        s1.name = "John";
        assertEquals("1 John", s1.display());

        Student3 s2 = new Student3();
        s2.id = 2;
        s2.name = "Jane";
        assertEquals("2 Jane", s2.display());
    }
}
