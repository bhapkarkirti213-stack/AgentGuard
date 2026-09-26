import { network } from "hardhat";

async function main() {

    const { ethers } = await network.connect();

    console.log("\n======================================");
    console.log(" AgentGuard Sepolia End-to-End Test");
    console.log("======================================\n");


    // --------------------------------------------------
    // CONTRACT ADDRESSES
    // --------------------------------------------------

    const REGISTRY_ADDRESS =
        "0xD19597a1fD327B16CbCEEb8e22D5b299AAFBe6fE";

    const REPUTATION_ADDRESS =
        "0xE86D8823FF9E3BB2dAd8d3C73C035ED735e1f643";

    const VERIFIER_ADDRESS =
        "0x018530d40Cf4E0020F00c11765A3CCA758E3fa5a";

    const ESCROW_ADDRESS =
        "0x4c5aeBAb398a3277E4208eD8B7C2eff70f491d73";


    // --------------------------------------------------
    // NETWORK CHECK
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
            "Wrong network. Expected Sepolia."
        );
    }


    // --------------------------------------------------
    // BUYER
    // --------------------------------------------------

    const [buyer] =
        await ethers.getSigners();

    console.log(
        "\nBuyer:",
        buyer.address
    );


    // --------------------------------------------------
    // PROVIDER
    // --------------------------------------------------

    const providerKey =
        process.env.PROVIDER_PRIVATE_KEY;

    if (!providerKey) {
        throw new Error(
            "PROVIDER_PRIVATE_KEY is missing from .env"
        );
    }

    const provider =
        new ethers.Wallet(
            providerKey,
            ethers.provider
        );

    console.log(
        "Provider:",
        provider.address
    );


    if (
        buyer.address.toLowerCase() ===
        provider.address.toLowerCase()
    ) {
        throw new Error(
            "Buyer and provider must be different wallets."
        );
    }


    // --------------------------------------------------
    // LOAD ABIs
    // --------------------------------------------------

    const registryArtifact =
        await import(
            "../artifacts/contracts/AgentRegistry.sol/AgentRegistry.json",
            {
                with: { type: "json" }
            }
        );

    const reputationArtifact =
        await import(
            "../artifacts/contracts/Reputation.sol/Reputation.json",
            {
                with: { type: "json" }
            }
        );

    const verifierArtifact =
        await import(
            "../artifacts/contracts/ServiceVerifier.sol/ServiceVerifier.json",
            {
                with: { type: "json" }
            }
        );

    const escrowArtifact =
        await import(
            "../artifacts/contracts/Escrow.sol/Escrow.json",
            {
                with: { type: "json" }
            }
        );


    // --------------------------------------------------
    // CONTRACT INSTANCES
    // --------------------------------------------------

    const registry =
        new ethers.Contract(
            REGISTRY_ADDRESS,
            registryArtifact.default.abi,
            provider
        );

    const reputation =
        new ethers.Contract(
            REPUTATION_ADDRESS,
            reputationArtifact.default.abi,
            provider
        );

    const verifier =
        new ethers.Contract(
            VERIFIER_ADDRESS,
            verifierArtifact.default.abi,
            buyer
        );

    const escrow =
        new ethers.Contract(
            ESCROW_ADDRESS,
            escrowArtifact.default.abi,
            buyer
        );


    // --------------------------------------------------
    // STEP 1: REGISTER PROVIDER
    // --------------------------------------------------

    const agentId =
        "weather-agent-sepolia";

    console.log(
        "\n1. Checking provider registration..."
    );

    let existingAgent;

    try {

        existingAgent =
            await registry.getAgent(agentId);

    } catch {

        existingAgent = null;
    }


    if (
        existingAgent &&
        existingAgent.wallet !==
        ethers.ZeroAddress
    ) {

        console.log(
            "Provider already registered."
        );

        console.log(
            "Agent wallet:",
            existingAgent.wallet
        );

    } else {

        console.log(
            "Registering provider..."
        );

        const registerTx =
            await registry
                .connect(provider)
                .registerAgent(
                    agentId,
                    "weather-data"
                );

        console.log(
            "Registration TX:",
            registerTx.hash
        );

        await registerTx.wait();

        console.log(
            "Provider registration confirmed."
        );
    }


    // --------------------------------------------------
    // STEP 2: VERIFY REGISTRATION
    // --------------------------------------------------

    const agent =
        await registry.getAgent(agentId);

    console.log(
        "\nRegistered wallet:",
        agent.wallet
    );

    console.log(
        "Service type:",
        agent.serviceType
    );

    console.log(
        "Active:",
        agent.active
    );


    if (
        agent.wallet.toLowerCase() !==
        provider.address.toLowerCase()
    ) {
        throw new Error(
            "Registered provider does not match provider wallet."
        );
    }


    // --------------------------------------------------
    // STEP 3: CREATE REQUEST HASH
    // --------------------------------------------------

    const requestData =
        JSON.stringify({
            service: "weather-data",
            location: "Pune",
            requestedBy: buyer.address,
            agentId: agentId
        });

    const serviceHash =
        ethers.keccak256(
            ethers.toUtf8Bytes(
                requestData
            )
        );

    console.log(
        "\n2. Request hash:",
        serviceHash
    );


    // --------------------------------------------------
    // STEP 4: CREATE ESCROW
    // --------------------------------------------------

    const amount =
        ethers.parseEther("0.001");

    const latestBlock =
        await ethers.provider.getBlock(
            "latest"
        );

    const deadline =
        BigInt(
            latestBlock!.timestamp
        ) + 3600n;

    console.log(
        "\n3. Creating escrow..."
    );

    console.log(
        "Amount:",
        ethers.formatEther(amount),
        "ETH"
    );

    const escrowTx =
        await escrow.createEscrow(
            agentId,
            provider.address,
            serviceHash,
            deadline,
            {
                value: amount
            }
        );

    console.log(
        "Escrow TX:",
        escrowTx.hash
    );

    await escrowTx.wait();

    console.log(
        "Escrow created."
    );


    // --------------------------------------------------
    // STEP 5: GET ESCROW
    // --------------------------------------------------

    const escrowId =
        await escrow.getEscrowCount();

    console.log(
        "Escrow ID:",
        escrowId.toString()
    );

    const escrowData =
        await escrow.getEscrow(
            escrowId
        );

    console.log(
        "Buyer:",
        escrowData.buyer
    );

    console.log(
        "Provider:",
        escrowData.provider
    );

    console.log(
        "Amount:",
        ethers.formatEther(
            escrowData.amount
        ),
        "ETH"
    );


    // --------------------------------------------------
    // STEP 6: CREATE SERVICE VERIFICATION
    // --------------------------------------------------

    console.log(
        "\n4. Creating service verification..."
    );

    const verificationTx =
        await verifier.createVerification(
            escrowId,
            provider.address,
            serviceHash
        );

    console.log(
        "Verification creation TX:",
        verificationTx.hash
    );

    await verificationTx.wait();

    console.log(
        "Verification created."
    );


    // --------------------------------------------------
    // STEP 7: VERIFY SERVICE
    // --------------------------------------------------

    const resultData =
        JSON.stringify({
            temperature: 28.4,
            location: "Pune",
            source: "weather-agent-sepolia"
        });

    const resultHash =
        ethers.keccak256(
            ethers.toUtf8Bytes(
                resultData
            )
        );

    console.log(
        "\n5. Verifying service..."
    );

    const verifyTx =
        await verifier.verifyService(
            escrowId,
            resultHash,
            true
        );

    console.log(
        "Verification TX:",
        verifyTx.hash
    );

    await verifyTx.wait();

    console.log(
        "Service marked VALID."
    );


    // --------------------------------------------------
    // STEP 8: CHECK PROVIDER BALANCE
    // --------------------------------------------------

    const providerBefore =
        await ethers.provider.getBalance(
            provider.address
        );


    // --------------------------------------------------
    // STEP 9: RELEASE ESCROW
    // --------------------------------------------------

    console.log(
        "\n6. Releasing escrow..."
    );

    const releaseTx =
        await escrow.releaseVerifiedEscrow(
            escrowId
        );

    console.log(
        "Release TX:",
        releaseTx.hash
    );

    await releaseTx.wait();

    console.log(
        "Payment released."
    );


    // --------------------------------------------------
    // STEP 10: CHECK PAYMENT
    // --------------------------------------------------

    const providerAfter =
        await ethers.provider.getBalance(
            provider.address
        );

    console.log(
        "\nProvider balance change:"
    );

    console.log(
        ethers.formatEther(
            providerAfter -
            providerBefore
        ),
        "ETH"
    );


    // --------------------------------------------------
    // STEP 11: CHECK ESCROW STATUS
    // --------------------------------------------------

    const finalEscrow =
        await escrow.getEscrow(
            escrowId
        );

    console.log(
        "\nEscrow status:",
        finalEscrow.status.toString()
    );

    if (
        finalEscrow.status !== 2n
    ) {
        throw new Error(
            "Escrow was not released."
        );
    }


    // --------------------------------------------------
    // STEP 12: CHECK REPUTATION
    // --------------------------------------------------

    const reputationData =
        await reputation.getReputation(
            provider.address
        );

    const reputationScore =
        await reputation.getReputationScore(
            provider.address
        );

    console.log(
        "\n7. Provider reputation"
    );

    console.log(
        "Successful transactions:",
        reputationData.successfulTransactions.toString()
    );

    console.log(
        "Failed transactions:",
        reputationData.failedTransactions.toString()
    );

    console.log(
        "Refunded transactions:",
        reputationData.refundedTransactions.toString()
    );

    console.log(
        "Successful value:",
        ethers.formatEther(
            reputationData.successfulTransactionValue
        ),
        "ETH"
    );

    console.log(
        "Reputation score:",
        reputationScore.toString()
    );


    // --------------------------------------------------
    // FINAL RESULT
    // --------------------------------------------------

    console.log(
        "\n======================================"
    );

    console.log(
        " AgentGuard End-to-End Test SUCCESS"
    );

    console.log(
        "======================================"
    );

    console.log(
        "\nEscrow ID:",
        escrowId.toString()
    );

    console.log(
        "Amount:",
        ethers.formatEther(amount),
        "ETH"
    );

    console.log(
        "Release TX:",
        releaseTx.hash
    );

    console.log(
        "Reputation:",
        reputationScore.toString()
    );

    console.log(
        "\nAll operations occurred on Ethereum Sepolia."
    );
}


main().catch((error) => {

    console.error(error);

    process.exitCode = 1;

});