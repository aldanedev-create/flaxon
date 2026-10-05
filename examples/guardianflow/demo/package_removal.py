async def run(state, simulator):
    await simulator.run("package_removal", state.ingest)
