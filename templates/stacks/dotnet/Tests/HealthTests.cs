using Xunit;

public class HealthTests
{
    [Fact]
    public void StatusIsOk()
    {
        Assert.Equal("{ status = ok }", Health.Status().ToString());
    }
}
