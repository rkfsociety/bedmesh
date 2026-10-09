const PLATFORM_TAGS = new Set(["win", "mac", "android"]);

function compareVersions(left, right) {
  const a = left.split(".").map(Number);
  const b = right.split(".").map(Number);
  const length = Math.max(a.length, b.length);
  for (let i = 0; i < length; i += 1) {
    const difference = (a[i] || 0) - (b[i] || 0);
    if (difference !== 0) return difference;
  }
  return 0;
}

module.exports = async function prunePlatformReleases({ github, context, core, platform }) {
  if (!PLATFORM_TAGS.has(platform)) {
    throw new Error(`Unsupported platform release suffix: ${platform}`);
  }

  const { owner, repo } = context.repo;
  const releases = await github.paginate(github.rest.repos.listReleases, {
    owner,
    repo,
    per_page: 100,
  });
  const candidates = releases.flatMap((release) => {
    const match = /^v(\d+(?:\.\d+)+)-(win|mac|android)$/.exec(release.tag_name);
    if (!match || match[2] !== platform || release.draft || release.prerelease) return [];
    return [{ release, version: match[1] }];
  });

  candidates.sort((a, b) => compareVersions(b.version, a.version));
  const latest = candidates[0];
  if (!latest) {
    core.info(`No published stable releases found for ${platform}.`);
    return;
  }

  core.info(`Keeping ${latest.release.tag_name} as the latest ${platform} release.`);
  for (const { release } of candidates.slice(1)) {
    core.info(`Deleting obsolete release ${release.tag_name}. Git tag is retained.`);
    await github.rest.repos.deleteRelease({ owner, repo, release_id: release.id });
  }
};
