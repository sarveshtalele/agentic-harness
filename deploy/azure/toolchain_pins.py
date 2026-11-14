"""Pinned toolchain versions and the vendors' published hashes for toolchains.py. Change version, url and digest together."""

ALL = ("node", "java", "maven", "dotnet", "go", "chromium")

# Pins checked 2026-11-14 against the vendors' own checksum files (nodejs.org SHASUMS256.txt, go.dev/dl JSON, the .NET
# release-metadata JSON, the Adoptium assets API, archive.apache.org .sha512). To update: change version, url and digest together.
# dir is the folder name under ROOT; strip is the number of leading path parts removed on extraction; bins are relative to dir.
TOOLS = {
    "node": {"dir": "node-22.12.0", "strip": 1, "bins": ["bin"], "check": "bin/node", "algo": "sha256",
             "url": "https://nodejs.org/dist/v22.12.0/node-v22.12.0-linux-x64.tar.xz",
             "digest": "22982235e1b71fa8850f82edd09cdae7e3f32df1764a9ec298c72d25ef2c164f"},
    "java": {"dir": "jdk-21.0.13", "strip": 1, "bins": ["bin"], "check": "bin/java", "algo": "sha256", "env": {"JAVA_HOME": "."},
             "url": "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.13%2B9/OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz",
             "digest": "d7f5d5cf865a2902b70ff549b97586a7d3f234e016f041ab447ea740c7d66d1c"},
    "maven": {"dir": "maven-3.9.9", "strip": 1, "bins": ["bin"], "check": "bin/mvn", "algo": "sha512",
              "url": "https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.tar.gz",
              "digest": "a555254d6b53d267965a3404ecb14e53c3827c09c3b94b5678835887ab404556bfaf78dcfe03ba76fa2508649dca8531c74bca4d5846513522404d48e8c4ac8b"},
    "dotnet": {"dir": "dotnet-8.0.428", "strip": 0, "bins": ["."], "check": "dotnet", "algo": "sha512", "env": {"DOTNET_ROOT": "."},
               "url": "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.428/dotnet-sdk-8.0.428-linux-x64.tar.gz",
               "digest": "33212bb99a2bf003973d41106c7e8fe94208a12958ff601d4a476be379403c85a7dc9183a6ec64dfb44ded7102965be09f35add1758e68e9251bae7891d7b7bf"},
    "go": {"dir": "go-1.23.4", "strip": 1, "bins": ["bin"], "check": "bin/go", "algo": "sha256", "env": {"GOROOT": "."},
           "url": "https://go.dev/dl/go1.23.4.linux-amd64.tar.gz",
           "digest": "6924efde5de86fe277676e929dc9917d466efa02fb934197bc2eba35d5680971"},
}
# .NET without ICU (the base image may not have libicu), telemetry off. Kept here so the API process and a manual run agree.
FIXED_ENV = {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1", "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"}
