import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const SignetRegistryModule = buildModule("SignetRegistryModule", (m) => {
  // Deploy Signet contract
  const SignetRegistry = m.contract("SignetRegistry");

  return { SignetRegistry };
});

export default SignetRegistryModule;