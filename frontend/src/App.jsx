import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';

import { Layout } from './components/Layout.jsx';
import { PracticePage } from './pages/PracticePage.jsx';
import { SegmentListPage } from './pages/SegmentListPage.jsx';
import { VideoListPage } from './pages/VideoListPage.jsx';

function NotFoundPage() {
  return (
    <div className="stack">
      <div className="page-intro">
        <h1>找不到這個頁面</h1>
        <p>這個網址沒有對應的練習頁。</p>
      </div>
      <Link className="button not-found-link" to="/">
        回到影片列表
      </Link>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<VideoListPage />} />
          <Route path="/videos/:id" element={<SegmentListPage />} />
          <Route path="/videos/:id/segments/:position" element={<PracticePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
