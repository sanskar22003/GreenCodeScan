**Prerequisite of GTest**
Windows:

<br>1. Clone Git Library: https://github.com/google/googletest.git
<br>2. MS Build C++ Tools Installer: Microsoft C++ Build Tools - Visual Studio 
<br>3. Cmake: Download CMake (Install cmake-3.30.3-windows-x86_64.msi) 
<br>(verify cmake version using cmake --version)
<br>4. MinGW:  MinGW - Minimalist GNU for Windows download | SourceForge.net
<br>(Select G++ while installing)
<br>
	**<br>1. Run the below commands in CMD:
	<br>	a. git clone https://github.com/google/googletest.git
	<br>	b. Cd googletest
	<br>	c. Cmake . 
	<br>	d. nmake**

<br>=========================================================================================================

![image](https://github.com/user-attachments/assets/4f902173-a789-43e2-88ea-6d83619604d4)


<br>	• Download .NET SDK: Download .NET (Linux, macOS, and Windows) (microsoft.com)
<br>
<br>	• Verify using, dotnet --version
<br>
<br>	• (Optional) - To create a C# Project 
<br>		○ dotnet new console -o MyCSharpApp
<br>		○ cd MyCSharpApp
<br>		
<br>	• Install Nunit Framework and TestRunner
<br>		○ dotnet add package Nunit
<br>		○ dotnet add package NUnit3TestAdapter
<br>		○ To confirm installation, dotnet restore
<br>		
<br>	• (Optional) Write simple Nunit Test:
<br>		○ mkdir Tests
<br>		○ cd Tests
<br>		
<br>	• Create a test file SampleTest.cs inside the Tests folder:
<br>	
<br>	• To Run the test, dotnet test
<br>		
<br>
<br>
<br>
<br>Common error may occurs!!

<br>In 'dotnet test'
<br>![image](https://github.com/user-attachments/assets/827b3246-0522-4cd1-a8d4-18efc3e4df0b)

<br>
<br>	
<br>	1. Ensure project root Have a .csproj File (mostly it is there)
<br>	2. First, Go to root directory and run the "dotnet new nunit -o Tests" Command
<br>	3. Cd to 'Tests' folder
<br>	4. Run - dotnet add reference "C:/Users/sansk/OneDrive/Desktop/E-Commerce Application/MyCSharpApp/MyCSharpApp.csproj"
<br>	5. Then move the test file into Tests folder using - move "C:\Users\sansk\OneDrive\Desktop\E-Commerce Application\MyCSharpApp\Tests\SampleTest.cs" <br>"C:\Users\sansk\OneDrive\Desktop\E-Commerce Application\MyCSharpApp\Tests"

<br>In 'dotnet test'

![image](https://github.com/user-attachments/assets/1d87ce2e-1980-4c18-8369-059c36f59870)


<br>	• REASONE: package version mismatch between the test project (Tests) and the main application (MyCSharpApp)
<br>
<br>		○ Then you have to run the below command for both Test and Root folder:
<br>
<br>			§ dotnet add package NUnit --version 4.2.2
<br>			§ dotnet add package NUnit3TestAdapter --version 4.6.0
<br>		○ Dotnet clean
<br>		○ Dotnet restore
<br>	
<br>		○ Run, dotnet test
			

 
