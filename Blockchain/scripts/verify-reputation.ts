import "dotenv/config";
import { network } from "hardhat";

const REPUTATION_ADDRESS =
    "0xF3CFCc90EdE1A7c5A5bE7A9EF2bF15E80dc55Ca0";

async function main() {

    const { ethers } = await network.create();

    const [deployer] = await ethers.getSigners();

    console.log("Connected wallet:");
    console.log(deployer.address);

    const reputation = await ethers.getContractAt(
        "Reputation",
        REPUTATION_ADDRESS
    );

    // 1. Read owner
    const owner = await reputation.owner();

    console.log("\nOwner:");
    console.log(owner);

    // 2. Check whether deployer is authorized
    const authorized =
        await reputation.authorizedUpdaters(
            deployer.address
        );

    console.log("\nDeployer authorized:");
    console.log(authorized);

    // 3. Read current reputation
    let data = await reputation.getReputation(
        deployer.address
    );

    console.log("\nCurrent reputation:");
    console.log("Successful:", data.successfulTransactions.toString());
    console.log("Failed:", data.failedTransactions.toString());
    console.log("Refunded:", data.refundedTransactions.toString());
    console.log("Disputes:", data.disputes.toString());
    console.log(
        "Total value:",
        ethers.formatEther(data.totalTransactionValue),
        "ETH"
    );

    console.log(
        "Current score:",
        (await reputation.getReputationScore(
            deployer.address
        )).toString()
    );

    // 4. Record one REAL successful transaction
    console.log("\nSubmitting real Sepolia reputation transaction...");

    const tx = await reputation.recordSuccess(
        deployer.address,
        ethers.parseEther("0.001")
    );

    console.log("Transaction hash:");
    console.log(tx.hash);

    // 5. Wait for blockchain confirmation
    const receipt = await tx.wait();

    console.log("\nTransaction confirmed.");
    console.log("Block number:", receipt?.blockNumber);

    // 6. Read reputation again from blockchain
    data = await reputation.getReputation(
        deployer.address
    );

    console.log("\nUpdated reputation:");
    console.log("Successful:", data.successfulTransactions.toString());
    console.log("Failed:", data.failedTransactions.toString());
    console.log("Refunded:", data.refundedTransactions.toString());
    console.log("Disputes:", data.disputes.toString());

    console.log(
        "Total value:",
        ethers.formatEther(data.totalTransactionValue),
        "ETH"
    );

    console.log(
        "Updated score:",
        (await reputation.getReputationScore(
            deployer.address
        )).toString()
    );

    console.log(
        "\nEtherscan transaction:"
    );

    console.log(
        `https://sepolia.etherscan.io/tx/${tx.hash}`
    );
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});