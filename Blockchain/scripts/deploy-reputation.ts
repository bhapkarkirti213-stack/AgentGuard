import { network } from "hardhat";

async function main() {
    const { ethers } = await network.create();

    const [deployer] = await ethers.getSigners();

    console.log("Deploying Reputation contract...");
    console.log("Deployer:", deployer.address);

    const balance = await ethers.provider.getBalance(
        deployer.address
    );

    console.log(
        "Deployer balance:",
        ethers.formatEther(balance),
        "ETH"
    );

    const reputation = await ethers.deployContract(
        "Reputation"
    );

    await reputation.waitForDeployment();

    const address = await reputation.getAddress();

    console.log("Reputation deployed to:", address);

    console.log(
        "Owner:",
        await reputation.owner()
    );

    console.log(
        "Deployer authorized:",
        await reputation.authorizedUpdaters(
            deployer.address
        )
    );
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});