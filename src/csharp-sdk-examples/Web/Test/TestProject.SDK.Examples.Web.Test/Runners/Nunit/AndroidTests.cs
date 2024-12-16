﻿using NUnit.Framework;
using TestProject.SDK.Examples.Web.Runners.Nunit.Base;

namespace TestProject.SDK.Examples.Web.Runners.Nunit
{
	[TestFixture]
	public class AndroidTests : TestBase
	{
		Runner runner;

		[OneTimeSetUp]
		public void SetUp()
		{
			runner = new RunnerBuilder(DevToken)
				.AsAndroidWeb(AndroidDeviceUDID).Build();
		}

		[Test]
		public void RunTest()
		{
			RunTest(runner);
		}

		[Test]
		public void RunExtendedTest()
		{
			RunExtendedTest(runner);
		}

		[Test]
		public void RunProxyTest()
		{
			RunProxyTest(runner);
		}

		[OneTimeTearDown]
		public void TearDown()
		{
			runner.Dispose();
		}
	}
}