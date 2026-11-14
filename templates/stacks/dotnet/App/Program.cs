var app = WebApplication.CreateBuilder(args).Build();
app.MapGet("/health", () => Health.Status());
app.Run();
