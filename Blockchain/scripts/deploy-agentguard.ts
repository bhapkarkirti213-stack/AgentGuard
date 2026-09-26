import { network } from "hardhat";

async function main() {

    const { ethers } = await network.connect();

    console.log("\n======================================");
    console.log("     AgentGuard Sepolia Deployment");
    console.log("======================================\n");


    // --------------------------------------------------
    // NETWORK
    // --------------------------------------------------

    const networkInfo =
        await ethers.provider.getNetwork();

    console.log(
        "Chain ID:",
        networkInfo.chainId.toString()
    );

    if (
        networkInfo.chainId !== 11155111n
    ) {
        throw new Error(
            "Wrong network. Expected Ethereum Sepolia."
        );
    }


    // --------------------------------------------------
    // DEPLOYER
    // --------------------------------------------------

    const [deployer] =
        await ethers.getSigners();

    console.log(
        "Deployer:",
        deployer.address
    );

    const balance =
        await ethers.provider.getBalance(
            deployer.address
        );

    console.log(
        "Balance:",
        ethers.formatEther(balance),
        "ETH\n"
    );


    // --------------------------------------------------
    // 1. DEPLOY AGENT REGISTRY
    // --------------------------------------------------

    console.log(
        "1/4 Deploying AgentRegistry..."
    );

    const registry =
        await ethers.deployContract(
            "AgentRegistry"
        );

    await registry.waitForDeployment();

    const registryAddress =
        await registry.getAddress();

    console.log(
        "AgentRegistry:",
        registryAddress
    );


    // --------------------------------------------------
    // 2. DEPLOY REPUTATION
    // --------------------------------------------------

    console.log(
        "\n2/4 Deploying Reputation..."
    );

    const reputation =
        await ethers.deployContract(
            "Reputation"
        );

    await reputation.waitForDeployment();

    const reputationAddress =
        await reputation.getAddress();

    console.log(
        "Reputation:",
        reputationAddress
    );


    // --------------------------------------------------
    // 3. DEPLOY SERVICE VERIFIER
    // --------------------------------------------------

    console.log(
        "\n3/4 Deploying ServiceVerifier..."
    );

    const verifier =
        await ethers.deployContract(
            "ServiceVerifier"
        );

    await verifier.waitForDeployment();

    const verifierAddress =
        await verifier.getAddress();

    console.log(
        "ServiceVerifier:",
        verifierAddress
    );


    // --------------------------------------------------
    // 4. DEPLOY ESCROW
    // --------------------------------------------------

    console.log(
        "\n4/4 Deploying Escrow..."
    );

    const escrow =
        await ethers.deployContract(
            "Escrow"
        );

    await escrow.waitForDeployment();

    const escrowAddress =
        await escrow.getAddress();

    console.log(
        "Escrow:",
        escrowAddress
    );


    // --------------------------------------------------
    // CONFIGURE ESCROW
    // --------------------------------------------------

    console.log(
        "\nConfiguring Escrow..."
    );


    console.log(
        "Setting AgentRegistry..."
    );

    const tx1 =
        await escrow.setAgentRegistry(
            registryAddress
        );

    await tx1.wait();


    console.log(
        "Setting Reputation..."
    );

    const tx2 =
        await escrow.setReputationContract(
            reputationAddress
        );

    await tx2.wait();


    console.log(
        "Setting ServiceVerifier..."
    );

    const tx3 =
        await escrow.setServiceVerifier(
            verifierAddress
        );

    await tx3.wait();


    // --------------------------------------------------
    // AUTHORIZE ESCROW IN REPUTATION
    // --------------------------------------------------

    console.log(
        "\nAuthorizing Escrow in Reputation..."
    );

    const tx4 =
        await reputation.setAuthorizedUpdater(
            escrowAddress,
            true
        );

    await tx4.wait();


    // --------------------------------------------------
    // VERIFY CONFIGURATION
    // --------------------------------------------------

    console.log(
        "\nChecking configuration..."
    );

    const configuredRegistry =
        await escrow.agentRegistry();

    const configuredReputation =
        await escrow.reputation();

    const configuredVerifier =
        await escrow.serviceVerifier();

    const escrowAuthorized =
        await reputation.authorizedUpdaters(
            escrowAddress
        );


    console.log(
        "Escrow → AgentRegistry:",
        configuredRegistry
    );

    console.log(
        "Escrow → Reputation:",
        configuredReputation
    );

    console.log(
        "Escrow → ServiceVerifier:",
        configuredVerifier
    );

    console.log(
        "Escrow authorized in Reputation:",
        escrowAuthorized
    );


    // --------------------------------------------------
    // FINAL VALIDATION
    // --------------------------------------------------

    if (
        configuredRegistry.toLowerCase() !==
        registryAddress.toLowerCase()
    ) {
        throw new Error(
            "AgentRegistry configuration failed."
        );
    }

    if (
        configuredReputation.toLowerCase() !==
        reputationAddress.toLowerCase()
    ) {
        throw new Error(
            "Reputation configuration failed."
        );
    }

    if (
        configuredVerifier.toLowerCase() !==
        verifierAddress.toLowerCase()
    ) {
        throw new Error(
            "ServiceVerifier configuration failed."
        );
    }

    if (!escrowAuthorized) {
        throw new Error(
            "Escrow was not authorized in Reputation."
        );
    }


    // --------------------------------------------------
    // FINAL OUTPUT
    // --------------------------------------------------

    console.log(
        "\n======================================"
    );

    console.log(
        " AgentGuard Deployment Successful"
    );

    console.log(
        "======================================\n"
    );

    console.log(
        "AgentRegistry:",
        registryAddress
    );

    console.log(
        "Reputation:",
        reputationAddress
    );

    console.log(
        "ServiceVerifier:",
        verifierAddress
    );

    console.log(
        "Escrow:",
        escrowAddress
    );

    console.log(
        "\nNetwork: Ethereum Sepolia"
    );

    console.log(
        "Chain ID: 11155111"
    );

    console.log(
        "\n======================================\n"
    );
}


main().catch((error) => {

    console.error(error);

    process.exitCode = 1;

});