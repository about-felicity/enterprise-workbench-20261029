import CreatorVideos from "../CreatorVideos";
import WorkbenchLogo from "../WorkbenchLogo";

export default function EmployeeVideosPage() {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><WorkbenchLogo /></div>
          <span><b>企业工作台</b><span className="brand-meta"><small>员工视频</small></span></span>
        </div>
        <nav aria-label="工作台">
          <button type="button" className="active" aria-current="page"><span><b>自有员工视频数据</b></span></button>
        </nav>
        <div className="sidebar-tools"><a className="asset-entry" href="/geo_monitor/logout"><span>退出登录</span></a></div>
      </aside>
      <section className="workspace">
        <header className="topbar"><h1>自有员工视频数据</h1></header>
        <div className="content"><CreatorVideos ledger="employee-videos" /></div>
      </section>
    </main>
  );
}
