using System;
using System.Collections.Generic;
using System.Threading;

namespace SampleDotNetApp
{
    class InefficientProgram
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Welcome to the Inefficient .NET Application!");

            // Unnecessary delay
            Thread.Sleep(2000);

            Console.Write("Enter the first number: ");
            double num1 = Convert.ToDouble(Console.ReadLine());

            // Unnecessary loop
            for (int i = 0; i < 1000000; i++)
            {
                num1 += 0.000001;
            }

            Console.Write("Enter the second number: ");
            double num2 = Convert.ToDouble(Console.ReadLine());

            // Unnecessary loop
            for (int i = 0; i < 1000000; i++)
            {
                num2 += 0.000001;
            }

            Console.WriteLine("Choose an operation:");
            Console.WriteLine("1. Addition");
            Console.WriteLine("2. Subtraction");
            Console.WriteLine("3. Multiplication");
            Console.WriteLine("4. Division");

            int choice = Convert.ToInt32(Console.ReadLine());

            double result = 0;

            // Inefficient data structure
            Dictionary<int, Func<double, double, double>> operations = new Dictionary<int, Func<double, double, double>>
            {
                { 1, Add },
                { 2, Subtract },
                { 3, Multiply },
                { 4, Divide }
            };

            if (operations.ContainsKey(choice))
            {
                result = operationschoice;
            }
            else
            {
                Console.WriteLine("Invalid choice.");
            }

            // Unnecessary delay
            Thread.Sleep(2000);

            Console.WriteLine($"The result is: {result}");
        }

        static double Add(double a, double b)
        {
            // Redundant computation
            for (int i = 0; i < 1000000; i++) { }
            return a + b;
        }

        static double Subtract(double a, double b)
        {
            // Redundant computation
            for (int i = 0; i < 1000000; i++) { }
            return a - b;
        }

        static double Multiply(double a, double b)
        {
            // Redundant computation
            for (int i = 0; i < 1000000; i++) { }
            return a * b;
        }

        static double Divide(double a, double b)
        {
            // Redundant computation
            for (int i = 0; i < 1000000; i++) { }
            if (b != 0)
            {
                return a / b;
            }
            else
            {
                Console.WriteLine("Cannot divide by zero.");
                return 0;
            }
        }
    }
}
