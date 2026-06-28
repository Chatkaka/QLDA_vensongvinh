// ==========================================
// HỆ THỐNG QUẢN LÝ VÒNG ĐỜI GÓI THẦU - LOGIC
// ==========================================

// Biến lưu trữ trạng thái ứng dụng toàn cục
let state = {
  master: [],
  so01: [],
  so02: [],
  so03: [],
  so04: [],
  so05: []
};

// Trạng thái Tab hiện tại
let currentTab = "dashboard";

// Các biến trạng thái của Tab Master
let currentMasterSubTab = "cdt";
let currentMasterViewLevel = "detail";

// Khởi chạy ứng dụng
document.addEventListener("DOMContentLoaded", () => {
  initSystem();
  setupEventListeners();
  startClock();
});

// 1. KHỞI TẠO HỆ THỐNG & ĐỒNG BỘ DỮ LIỆU LOCALSTORAGE
function initSystem() {
  const savedData = localStorage.getItem("VND_TENDER_SYSTEM_STATE");
  
  if (savedData) {
    try {
      state = JSON.parse(savedData);
    } catch (e) {
      console.error("Lỗi đọc dữ liệu từ LocalStorage, đang nạp lại dữ liệu mẫu", e);
      state = JSON.parse(JSON.stringify(INITIAL_DATA));
    }
  } else {
    // Nạp dữ liệu mẫu ban đầu từ data_mock.js
    state = JSON.parse(JSON.stringify(INITIAL_DATA));
  }
  
  // Thực hiện tính toán tự động hóa các công thức liên kết
  recalculateAllFormulas();
  
  // Lưu lại trạng thái chuẩn hóa
  saveStateToStorage(false); // Không render lại để tránh lặp vô tận khi init
  
  // Hiển thị giao diện tab mặc định
  switchTab("dashboard");
  
  // Áp dụng theme đã lưu
  const savedTheme = localStorage.getItem("VND_TENDER_THEME") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeButtonIcon(savedTheme);
  
  // Khởi tạo cài đặt AI
  initAiSettings();
}

// Lưu dữ liệu vào LocalStorage và cập nhật giao diện
function saveStateToStorage(shouldRender = true) {
  localStorage.setItem("VND_TENDER_SYSTEM_STATE", JSON.stringify(state));
  
  if (shouldRender) {
    recalculateAllFormulas();
    updateDashboard();
    renderCurrentTab();
  }
}

// Khôi phục dữ liệu mẫu gốc
function resetToMockData() {
  if (confirm("Bạn có chắc chắn muốn khôi phục toàn bộ dữ liệu về trạng thái mẫu ban đầu không? Mọi thay đổi hiện tại của bạn sẽ bị xóa.")) {
    state = JSON.parse(JSON.stringify(INITIAL_DATA));
    recalculateAllFormulas();
    saveStateToStorage(true);
    alert("Đã khôi phục dữ liệu mẫu thành công!");
    switchTab("dashboard");
  }
}

// 2. CÔNG THỨC & TỰ ĐỘNG HÓA LIÊN KẾT (RELATIONAL FORMULAS)
function recalculateAllFormulas() {
  if (!state.master) state.master = [];
  if (!state.so01) state.so01 = [];
  if (!state.so02) state.so02 = [];
  if (!state.so03) state.so03 = [];
  if (!state.so04) state.so04 = [];
  if (!state.so05) state.so05 = [];

  state.master.forEach((row, idx) => {
    // Tự động gán STT dựa trên thứ tự dòng nếu chưa có
    if (row.tt === undefined || row.tt === null || row.tt === "") {
      row.tt = idx + 1;
    }
    
    // Ràng buộc kiểu dữ liệu số
    const nganSach = parseFloat(row.nganSach) || 0;
    const giaTriHdcu = parseFloat(row.giaTriHdcu) || 0;
    row.nganSach = nganSach;
    row.giaTriHdcu = giaTriHdcu;
    
    // 2.1. Công thức % HĐCU/NS
    if (nganSach > 0) {
      row.tileHdcuNs = parseFloat(((giaTriHdcu / nganSach) * 100).toFixed(2));
    } else {
      row.tileHdcuNs = 0;
    }
    
    // 2.2. Công thức ĐIỀU KIỆN ĐỦ Khởi công
    const dk1 = (row.dk1 || "Chưa đạt").trim() === "Đạt";
    const dk2 = (row.dk2 || "Chưa đạt").trim() === "Đạt";
    const dk3 = (row.dk3 || "Chưa đạt").trim() === "Đạt";
    if (dk1 && dk2 && dk3) {
      row.dieuKienDu = "ĐỦ ĐIỀU KIỆN KHỞI CÔNG";
    } else {
      row.dieuKienDu = "CHƯA ĐỦ";
    }
    
    // 2.3. Lũy kế giá trị HĐ A-B gốc
    // Nếu chưa nhập thì mặc định bằng giá trị hợp đồng cung ứng
    if (row.luyKeGiaTriHdAB === undefined || row.luyKeGiaTriHdAB === null || row.luyKeGiaTriHdAB === "" || row.luyKeGiaTriHdAB === 0) {
      row.luyKeGiaTriHdAB = giaTriHdcu;
    } else {
      row.luyKeGiaTriHdAB = parseFloat(row.luyKeGiaTriHdAB) || 0;
    }
    
    // 2.4. Công thức Lũy kế phát sinh HĐ B-B' từ Sổ 03
    let sumPhatSinh = 0;
    state.so03.forEach(ps => {
      if (ps.maBsc === row.maBsc && ps.ttDuyet === "Đã duyệt") {
        sumPhatSinh += parseFloat(ps.giaTri) || 0;
      }
    });
    row.luyKePhatSinhBB = parseFloat(sumPhatSinh.toFixed(4));
    
    // 2.5. Công thức Lũy kế tổng chi phí = Lũy kế HĐ A-B + Lũy kế phát sinh B-B'
    row.luyKeTongChiPhi = parseFloat((row.luyKeGiaTriHdAB + row.luyKePhatSinhBB).toFixed(4));
    
    // 2.6. Đồng bộ liên kết Sổ 01 (Hồ sơ tiền khởi công đã duyệt)
    const hsDuyetList = [];
    state.so01.forEach(hs => {
      if (hs.maBsc === row.maBsc && hs.ttDuyet === "Đã duyệt") {
        hsDuyetList.push(hs.loaiHoSo);
      }
    });
    row.hsTienKc = hsDuyetList.length > 0 ? hsDuyetList.join(", ") : "Chưa có HS duyệt";
    
    // 2.7. Đồng bộ liên kết Sổ 02 (Tài liệu KH tháng: Duyệt / Tổng của tháng hiện tại - mặc định Tháng 06/2026)
    let khThangTotal = 0;
    let khThangDuyet = 0;
    state.so02.forEach(kh => {
      if (kh.maBsc === row.maBsc && kh.thang === "Tháng 06/2026") {
        khThangTotal++;
        if (kh.ttDuyet === "Đã duyệt") {
          khThangDuyet++;
        }
      }
    });
    row.taiLieuKhThang = `${khThangDuyet}/${khThangTotal}`;
    
    // 2.8. Đếm số bản ghi phát sinh chờ duyệt ở Sổ 03
    let psChaoDuyet = 0;
    state.so03.forEach(ps => {
      if (ps.maBsc === row.maBsc && ps.ttDuyet === "Chờ duyệt") {
        psChaoDuyet++;
      }
    });
    row.phatSinhChuaDuyet = psChaoDuyet;
    
    // 2.9. Đếm số bản ghi YC cung ứng chờ duyệt ở Sổ 04
    let cuChaoDuyet = 0;
    state.so04.forEach(cu => {
      if (cu.maBsc === row.maBsc && cu.ttDuyet === "Chờ duyệt") {
        cuChaoDuyet++;
      }
    });
    row.cungUngChuaDuyet = cuChaoDuyet;
  });
  
  // Đồng bộ ngược lại tên hạng mục từ Master sang các Sổ nghiệp vụ phụ nếu có thay đổi hạng mục ở bảng Master
  state.so01.forEach(item => { item.hangMuc = getHangMucByMaBsc(item.maBsc); });
  state.so02.forEach(item => { item.hangMuc = getHangMucByMaBsc(item.maBsc); });
  state.so03.forEach(item => { item.hangMuc = getHangMucByMaBsc(item.maBsc); });
  state.so04.forEach(item => { item.hangMuc = getHangMucByMaBsc(item.maBsc); });
  state.so05.forEach(item => { item.hangMuc = getHangMucByMaBsc(item.maBsc); });
}

// Lấy tên hạng mục theo mã BSC
function getHangMucByMaBsc(maBsc) {
  const found = state.master.find(m => m.maBsc === maBsc);
  return found ? found.hangMuc : "Không xác định";
}

// 3. ĐIỀU HƯỚNG TABS & GIAO DIỆN CHÍNH
function setupEventListeners() {
  // Bắt sự kiện chuyển Tab điều hướng trên Sidebar
  document.querySelectorAll(".menu-link").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const tabName = link.getAttribute("data-tab");
      switchTab(tabName);
    });
  });
  
  // Nút Thêm mới bản ghi tương ứng từng tab
  document.getElementById("addNewRecordBtn").addEventListener("click", () => {
    openModalForTab(currentTab);
  });
  
  // Toggle theme Sáng/Tối
  document.getElementById("themeToggleBtn").addEventListener("click", () => {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("VND_TENDER_THEME", newTheme);
    updateThemeButtonIcon(newTheme);
  });
  
  // Reset dữ liệu mẫu
  document.getElementById("resetDataBtn").addEventListener("click", resetToMockData);
  
  // Export dữ liệu sang JSON
  document.getElementById("exportBtn").addEventListener("click", exportDataToJson);
  
  // Import dữ liệu từ JSON
  document.getElementById("importFileInput").addEventListener("change", importDataFromJson);
  
  // Bắt sự kiện đóng Modal ở tất cả các Modal close buttons và backdrop click
  document.querySelectorAll(".modal-backdrop").forEach(backdrop => {
    backdrop.addEventListener("click", (e) => {
      if (e.target === backdrop) {
        closeModal(backdrop.id);
      }
    });
    
    const closeBtn = backdrop.querySelector(".modal-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        closeModal(backdrop.id);
      });
    }
    
    const cancelBtn = backdrop.querySelector(".modal-cancel-btn");
    if (cancelBtn) {
      cancelBtn.addEventListener("click", (e) => {
        e.preventDefault();
        closeModal(backdrop.id);
      });
    }
  });
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Bảng Master
  document.getElementById("masterSearchInput").addEventListener("input", renderMasterTable);
  document.getElementById("masterFilterNhomCt").addEventListener("change", renderMasterTable);
  document.getElementById("masterFilterGoiThauPl").addEventListener("change", renderMasterTable);
  document.getElementById("masterFilterDieuKien").addEventListener("change", renderMasterTable);
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Sổ 01
  document.getElementById("so01SearchInput").addEventListener("input", renderSo01Table);
  document.getElementById("so01FilterBsc").addEventListener("change", renderSo01Table);
  document.getElementById("so01FilterStatus").addEventListener("change", renderSo01Table);
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Sổ 02
  document.getElementById("so02SearchInput").addEventListener("input", renderSo02Table);
  document.getElementById("so02FilterBsc").addEventListener("change", renderSo02Table);
  document.getElementById("so02FilterYckt").addEventListener("change", renderSo02Table);
  document.getElementById("so02FilterStatus").addEventListener("change", renderSo02Table);
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Sổ 03
  document.getElementById("so03SearchInput").addEventListener("input", renderSo03Table);
  document.getElementById("so03FilterBsc").addEventListener("change", renderSo03Table);
  document.getElementById("so03FilterLoai").addEventListener("change", renderSo03Table);
  document.getElementById("so03FilterStatus").addEventListener("change", renderSo03Table);
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Sổ 04
  document.getElementById("so04SearchInput").addEventListener("input", renderSo04Table);
  document.getElementById("so04FilterBsc").addEventListener("change", renderSo04Table);
  document.getElementById("so04FilterLoaiYc").addEventListener("change", renderSo04Table);
  document.getElementById("so04FilterStatus").addEventListener("change", renderSo04Table);
  
  // Đăng ký bộ lọc tìm kiếm & dropdown cho Sổ 05
  document.getElementById("so05SearchInput").addEventListener("input", renderSo05Table);
  document.getElementById("so05FilterBsc").addEventListener("change", renderSo05Table);
  document.getElementById("so05FilterStatus").addEventListener("change", renderSo05Table);
  
  // RÀNG BUỘC AUTO-FILL HẠNG MỤC THEO MÃ BSC TRONG CÁC FORM
  setupAutoFillForForm("so01MaBsc", "so01HangMuc");
  setupAutoFillForForm("so02MaBsc", "so02HangMuc");
  setupAutoFillForForm("so03MaBsc", "so03HangMuc");
  setupAutoFillForForm("so04MaBsc", "so04HangMuc");
  setupAutoFillForForm("so05MaBsc", "so05HangMuc");
  
  // Xử lý lưu các form
  document.getElementById("saveMasterBtn").addEventListener("click", saveMasterForm);
  document.getElementById("saveSo01Btn").addEventListener("click", saveSo01Form);
  document.getElementById("saveSo02Btn").addEventListener("click", saveSo02Form);
  document.getElementById("saveSo03Btn").addEventListener("click", saveSo03Form);
  document.getElementById("saveSo04Btn").addEventListener("click", saveSo04Form);
  document.getElementById("saveSo05Btn").addEventListener("click", saveSo05Form);

  // Đăng ký sự kiện AI Copilot
  document.getElementById("saveApiKeyBtn").addEventListener("click", saveApiKey);
  document.getElementById("aiProjectReportBtn").addEventListener("click", analyzeProjectWithAi);
  document.getElementById("chatToggleBtn").addEventListener("click", toggleChatWindow);
  document.getElementById("chatCloseBtn").addEventListener("click", toggleChatWindow);
  document.getElementById("chatSendBtn").addEventListener("click", sendChatMessage);
  document.getElementById("chatInput").addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });
  document.getElementById("copyAiReportBtn").addEventListener("click", copyAiReport);

  // Đăng ký sự kiện Excel
  document.getElementById("exportExcelBtn").addEventListener("click", exportToExcel);
  document.getElementById("importExcelInput").addEventListener("change", importFromExcel);

  // Đăng ký sự kiện AI Smart Import
  document.getElementById("importAiInput").addEventListener("change", importWithAi);
  document.getElementById("aiImportAppendBtn").addEventListener("click", () => applyAiImportData(false));
  document.getElementById("aiImportOverwriteBtn").addEventListener("click", () => applyAiImportData(true));
}

// Logic chuyển tab SPA
function switchTab(tabName) {
  currentTab = tabName;
  
  // Đặt trạng thái hoạt động trên sidebar menu
  document.querySelectorAll(".menu-link").forEach(link => {
    if (link.getAttribute("data-tab") === tabName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });
  
  // Ẩn toàn bộ nội dung tab và chỉ hiển thị tab đang chọn
  document.querySelectorAll(".tab-content").forEach(content => {
    if (content.id === `tab-${tabName}`) {
      content.classList.add("active");
    } else {
      content.classList.remove("active");
    }
  });
  
  // Cập nhật header title và văn bản nút thêm mới
  const titleEl = document.getElementById("currentTabTitle");
  const addBtn = document.getElementById("addNewRecordBtn");
  const addBtnText = document.getElementById("addNewRecordBtnText");
  
  // Hiển thị nút thêm mới (ẩn đi đối với tab dashboard)
  if (tabName === "dashboard") {
    addBtn.style.display = "none";
    titleEl.innerHTML = `<i class="fa-solid fa-chart-pie text-primary"></i> Dashboard tổng hợp dự án`;
  } else {
    addBtn.style.display = "inline-flex";
    
    switch (tabName) {
      case "master":
        titleEl.innerHTML = `<i class="fa-solid fa-database text-primary"></i> Bảng Master dữ liệu tổng hợp`;
        addBtnText.textContent = "Thêm gói thầu";
        break;
      case "so01":
        titleEl.innerHTML = `<i class="fa-solid fa-folder-open text-primary"></i> Sổ 01 - Hồ sơ Tiền Khởi Công`;
        addBtnText.textContent = "Thêm hồ sơ";
        break;
      case "so02":
        titleEl.innerHTML = `<i class="fa-solid fa-calendar-check text-primary"></i> Sổ 02 - Kế hoạch triển khai tháng/tuần`;
        addBtnText.textContent = "Thêm kế hoạch";
        break;
      case "so03":
        titleEl.innerHTML = `<i class="fa-solid fa-file-invoice-dollar text-primary"></i> Sổ 03 - Phát sinh hồ sơ HĐ B - B'`;
        addBtnText.textContent = "Thêm phát sinh";
        break;
      case "so04":
        titleEl.innerHTML = `<i class="fa-solid fa-truck-ramp-box text-primary"></i> Sổ 04 - Yêu cầu cung ứng đặc thù`;
        addBtnText.textContent = "Yêu cầu cung ứng";
        break;
      case "so05":
        titleEl.innerHTML = `<i class="fa-solid fa-business-time text-primary"></i> Sổ 05 - Bù tiến độ thi công`;
        addBtnText.textContent = "Thêm phương án bù";
        break;
    }
  }
  
  // Render dữ liệu của tab cụ thể
  recalculateAllFormulas(); // Đảm bảo đồng bộ trước khi render
  renderCurrentTab();
}

// Gọi hàm render dữ liệu tương ứng với Tab hiện tại
function renderCurrentTab() {
  switch (currentTab) {
    case "dashboard":
      updateDashboard();
      break;
    case "master":
      renderMasterTable();
      break;
    case "so01":
      populateBscDropdown("so01FilterBsc");
      renderSo01Table();
      break;
    case "so02":
      populateBscDropdown("so02FilterBsc");
      renderSo02Table();
      break;
    case "so03":
      populateBscDropdown("so03FilterBsc");
      renderSo03Table();
      break;
    case "so04":
      populateBscDropdown("so04FilterBsc");
      renderSo04Table();
      break;
    case "so05":
      populateBscDropdown("so05FilterBsc");
      renderSo05Table();
      break;
  }
}

// Cập nhật biểu tượng nút theme
function updateThemeButtonIcon(theme) {
  const btn = document.getElementById("themeToggleBtn");
  if (theme === "dark") {
    btn.innerHTML = `<i class="fa-solid fa-sun"></i> <span>Giao diện Sáng</span>`;
  } else {
    btn.innerHTML = `<i class="fa-solid fa-moon"></i> <span>Giao diện Tối</span>`;
  }
}

// Đồng hồ hiển thị thời gian ở Topbar
function startClock() {
  const clockEl = document.getElementById("currentTimeSpan");
  setInterval(() => {
    const now = new Date();
    const formatted = now.toLocaleDateString("vi-VN") + " " + now.toLocaleTimeString("vi-VN");
    clockEl.textContent = formatted;
  }, 1000);
}

// Thiết lập tự điền tên Hạng mục theo Mã BSC trong biểu mẫu
function setupAutoFillForForm(bscSelectId, hangMucInputId) {
  const selectEl = document.getElementById(bscSelectId);
  const inputEl = document.getElementById(hangMucInputId);
  
  if (selectEl && inputEl) {
    selectEl.addEventListener("change", () => {
      const selectedBsc = selectEl.value;
      if (selectedBsc) {
        inputEl.value = getHangMucByMaBsc(selectedBsc);
      } else {
        inputEl.value = "";
      }
    });
  }
}

// Đổ dữ liệu Mã BSC vào các Dropdown
function populateBscDropdown(dropdownId, selectValue = "") {
  const dropdown = document.getElementById(dropdownId);
  if (!dropdown) return;
  
  const currentSelect = selectValue || dropdown.value;
  
  // Khởi tạo option đầu tiên
  let html = `<option value="">${dropdownId.includes("Filter") ? "Tất cả Mã BSC" : "-- Chọn Mã BSC --"}</option>`;
  
  state.master.forEach(m => {
    html += `<option value="${m.maBsc}">${m.maBsc} (${m.hangMuc})</option>`;
  });
  
  dropdown.innerHTML = html;
  dropdown.value = currentSelect;
}

// 4. KẾT XUẤT DASHBOARD (KPI, BIỂU ĐỒ SVG, CẢNH BÁO)
function updateDashboard() {
  // KPI 1: Tổng ngân sách toàn dự án (tỷ)
  const totalBudget = state.master.reduce((sum, r) => sum + (parseFloat(r.nganSach) || 0), 0);
  document.getElementById("kpiTotalBudget").innerHTML = `${totalBudget.toLocaleString("vi-VN", {minimumFractionDigits: 1, maximumFractionDigits: 1})} <span class="kpi-unit">tỷ</span>`;
  
  // KPI 2: Tổng giá trị hợp đồng đã ký (tỷ)
  const totalContract = state.master.reduce((sum, r) => {
    if (r.ttHdcu === "Đã ký") {
      return sum + (parseFloat(r.giaTriHdcu) || 0);
    }
    return sum;
  }, 0);
  document.getElementById("kpiTotalContractSigned").innerHTML = `${totalContract.toLocaleString("vi-VN", {minimumFractionDigits: 1, maximumFractionDigits: 1})} <span class="kpi-unit">tỷ</span>`;
  
  // KPI 3: Tổng phát sinh đã duyệt (tỷ) (tính từ Sổ 03)
  const totalExtra = state.so03.reduce((sum, r) => {
    if (r.ttDuyet === "Đã duyệt") {
      return sum + (parseFloat(r.giaTri) || 0);
    }
    return sum;
  }, 0);
  document.getElementById("kpiTotalExtraApproved").innerHTML = `${totalExtra.toLocaleString("vi-VN", {minimumFractionDigits: 1, maximumFractionDigits: 2})} <span class="kpi-unit">tỷ</span>`;
  
  // KPI 4: Đếm gói thầu bị chậm tiến độ hoặc chưa đủ điều kiện khởi công
  const alertCount = state.master.filter(r => r.buTienDo === "Chậm tiến độ" || r.dieuKienDu === "CHƯA ĐỦ").length;
  document.getElementById("kpiAlertCount").textContent = alertCount;
  
  // 4.1. Vẽ Biểu đồ Donut SVG (Điều kiện khởi công)
  const duDkCount = state.master.filter(r => r.dieuKienDu === "ĐỦ ĐIỀU KIỆN KHỞI CÔNG").length;
  const chuaDuCount = state.master.length - duDkCount;
  const totalMaster = state.master.length || 1;
  const duPercentage = Math.round((duDkCount / totalMaster) * 100);
  
  // SVG Donut Params
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashOffset = circumference - (duPercentage / 100) * circumference;
  
  const donutSvg = document.getElementById("donutChartSvg");
  donutSvg.innerHTML = `
    <circle cx="80" cy="80" r="${radius}" fill="transparent" stroke="var(--border-color)" stroke-width="12"></circle>
    <circle cx="80" cy="80" r="${radius}" fill="transparent" stroke="var(--primary)" stroke-width="12"
      stroke-dasharray="${circumference}" stroke-dashoffset="${strokeDashOffset}"
      stroke-linecap="round"></circle>
  `;
  
  document.getElementById("donutChartCenterVal").textContent = `${duDkCount}/${state.master.length}`;
  
  // Tạo Legend Donut
  const donutLegend = document.getElementById("donutLegend");
  donutLegend.innerHTML = `
    <div class="legend-item">
      <div class="legend-label-wrapper">
        <span class="legend-color-dot" style="background-color: var(--primary);"></span>
        <span>Đủ ĐK Khởi công</span>
      </div>
      <span class="legend-val">${duDkCount} (${duPercentage}%)</span>
    </div>
    <div class="legend-item">
      <div class="legend-label-wrapper">
        <span class="legend-color-dot" style="background-color: var(--border-color);"></span>
        <span>Chưa đủ điều kiện</span>
      </div>
      <span class="legend-val">${chuaDuCount} (${100 - duPercentage}%)</span>
    </div>
  `;
  
  // 4.2. Vẽ Biểu đồ Cột SVG (Trạng thái LCNT)
  const lcntChuaTk = state.master.filter(r => r.ttLcnt === "Chưa triển khai").length;
  const lcntDangMoi = state.master.filter(r => r.ttLcnt === "Đang mời thầu").length;
  const lcntCoKq = state.master.filter(r => r.ttLcnt === "Đã có KQ").length;
  
  const barSvg = document.getElementById("barChartSvg");
  const lcntTotal = lcntChuaTk + lcntDangMoi + lcntCoKq || 1;
  const hChua = (lcntChuaTk / lcntTotal) * 100;
  const hMoi = (lcntDangMoi / lcntTotal) * 100;
  const hKq = (lcntCoKq / lcntTotal) * 100;
  
  barSvg.innerHTML = `
    <!-- Trục cơ bản -->
    <line x1="10%" y1="120" x2="90%" y2="120" stroke="var(--border-color)" stroke-width="2"></line>
    
    <!-- Cột Chưa triển khai -->
    <rect x="18%" y="${120 - hChua}" width="15%" height="${hChua}" rx="4" fill="var(--text-muted)"></rect>
    <text x="25.5%" y="${115 - hChua}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--text-main)">${lcntChuaTk}</text>
    
    <!-- Cột Đang mời thầu -->
    <rect x="42.5%" y="${120 - hMoi}" width="15%" height="${hMoi}" rx="4" fill="var(--warning)"></rect>
    <text x="50%" y="${115 - hMoi}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--text-main)">${lcntDangMoi}</text>
    
    <!-- Cột Đã có KQ -->
    <rect x="67%" y="${120 - hKq}" width="15%" height="${hKq}" rx="4" fill="var(--success)"></rect>
    <text x="74.5%" y="${115 - hKq}" text-anchor="middle" font-size="11" font-weight="700" fill="var(--text-main)">${lcntCoKq}</text>
  `;
  
  // Tạo Legend Cột
  const barLegend = document.getElementById("barLegend");
  barLegend.innerHTML = `
    <div class="legend-item" style="gap: 6px;">
      <span class="legend-color-dot" style="background-color: var(--text-muted);"></span>
      <span>Chưa TK (${lcntChuaTk})</span>
    </div>
    <div class="legend-item" style="gap: 6px;">
      <span class="legend-color-dot" style="background-color: var(--warning);"></span>
      <span>Mời thầu (${lcntDangMoi})</span>
    </div>
    <div class="legend-item" style="gap: 6px;">
      <span class="legend-color-dot" style="background-color: var(--success);"></span>
      <span>Đã có KQ (${lcntCoKq})</span>
    </div>
  `;
  
  // 4.3. Cảnh báo giám sát Dashboard
  const alertListContainer = document.getElementById("dashboardAlertList");
  alertListContainer.innerHTML = "";
  
  const alerts = [];
  
  // Thêm cảnh báo về chậm tiến độ
  state.master.forEach(r => {
    if (r.buTienDo === "Chậm tiến độ") {
      alerts.push({
        type: "error",
        title: `Gói thầu ${r.maBsc} chậm tiến độ`,
        desc: `${r.hangMuc} (Phụ trách: ${r.phuTrach || 'Chưa phân công'})`
      });
    } else if (r.dieuKienDu === "CHƯA ĐỦ" && r.ttLcnt === "Đã có KQ") {
      // Đã có kết quả thầu nhưng chưa đủ điều kiện khởi công
      alerts.push({
        type: "warning",
        title: `Gói thầu ${r.maBsc} chưa đạt ĐK khởi công`,
        desc: `Đã có KQ thầu nhưng ĐK kỹ thuật/hợp đồng chưa hoàn thiện`
      });
    }
  });
  
  // Thêm cảnh báo về phát sinh chưa duyệt (Sổ 03)
  state.so03.forEach(ps => {
    if (ps.ttDuyet === "Chờ duyệt") {
      alerts.push({
        type: "warning",
        title: `Yêu cầu phát sinh chưa duyệt [${ps.maPs}]`,
        desc: `Gói thầu ${ps.maBsc} - Giá trị: ${ps.giaTri} tỷ VNĐ (Chờ quyết định)`
      });
    }
  });
  
  // Thêm cảnh báo về yêu cầu cung ứng chưa duyệt (Sổ 04)
  state.so04.forEach(cu => {
    if (cu.ttDuyet === "Chờ duyệt") {
      alerts.push({
        type: "warning",
        title: `YC Cung ứng đặc thù chờ duyệt [${cu.maYc}]`,
        desc: `Gói thầu ${cu.maBsc} - Vật tư: ${cu.vatTu} (Giá trị: ${cu.giaTri} tỷ)`
      });
    }
  });
  
  if (alerts.length === 0) {
    alertListContainer.innerHTML = `
      <div class="table-empty-state" style="padding: 24px;">
        <div class="table-empty-icon" style="font-size: 1.8rem;"><i class="fa-solid fa-circle-check text-success" style="opacity:1;"></i></div>
        <div style="font-size: 0.8rem; font-weight:600; color:var(--text-main);">Hệ thống an toàn</div>
        <div style="font-size: 0.75rem; color:var(--text-muted); margin-top:2px;">Không có cảnh báo chậm tiến độ hoặc hồ sơ tồn đọng.</div>
      </div>
    `;
  } else {
    // Sắp xếp lỗi nghiêm trọng trước (error -> warning)
    alerts.sort((a, b) => (a.type === 'error' ? -1 : 1));
    
    // Hiển thị tối đa 5 cảnh báo mới nhất
    alerts.slice(0, 5).forEach(al => {
      const isError = al.type === "error";
      alertListContainer.innerHTML += `
        <div class="alert-item ${isError ? 'alert-error' : 'alert-warning'}">
          <span class="alert-item-icon">
            <i class="fa-solid ${isError ? 'fa-circle-exclamation' : 'fa-circle-question'}"></i>
          </span>
          <div class="alert-item-content">
            <div class="alert-item-title">${al.title}</div>
            <div class="alert-item-desc">${al.desc}</div>
          </div>
        </div>
      `;
    });
  }
}

// 5. RENDER CÁC BẢNG DỮ LIỆU CHUYÊN BIỆT

// 5.1. Render Bảng Master dữ liệu tổng hợp
// Helper định dạng số an toàn tránh crash JS
const formatNumberSafe = (val, decimals = 2, defaultVal = '0.00') => {
  if (val === undefined || val === null || val === "" || String(val).toLowerCase() === "nan") {
    return defaultVal;
  }
  const num = parseFloat(String(val).replace(/,/g, ''));
  return isNaN(num) ? defaultVal : num.toFixed(decimals);
};

// 5.1. Render Bảng Master dữ liệu tổng hợp
function renderMasterTable() {
  const searchVal = document.getElementById("masterSearchInput").value.toLowerCase().trim();
  const filterNhomCt = document.getElementById("masterFilterNhomCt").value;
  const filterGoiThau = document.getElementById("masterFilterGoiThauPl").value;
  const filterDieuKien = document.getElementById("masterFilterDieuKien").value;
  
  const tbody = document.getElementById("masterTableBody");
  tbody.innerHTML = "";
  
  // 1. Lọc dữ liệu thô ban đầu
  const filteredRaw = state.master.filter(r => {
    const searchMatch = !searchVal || 
                        (r.maBsc && r.maBsc.toLowerCase().includes(searchVal)) ||
                        (r.hangMuc && r.hangMuc.toLowerCase().includes(searchVal)) ||
                        (r.phuTrach && r.phuTrach.toLowerCase().includes(searchVal));
                        
    const nhomCtMatch = !filterNhomCt || r.nhomCt === filterNhomCt;
    const goiThauMatch = !filterGoiThau || r.goiThauPl === filterGoiThau;
    const dkMatch = !filterDieuKien || r.dieuKienDu === filterDieuKien;
    
    return searchMatch && nhomCtMatch && goiThauMatch && dkMatch;
  });
  
  // 2. Sắp xếp theo cấu trúc WBS phân cấp
  const parseTT = (ttVal) => {
    if (!ttVal) return [999999];
    return String(ttVal).split(/[\.-]/).map(p => {
      const num = parseFloat(p.trim());
      return isNaN(num) ? p.trim() : num;
    });
  };
  
  const sortedProjs = [...filteredRaw].sort((a, b) => {
    const tta = parseTT(a.tt);
    const ttb = parseTT(b.tt);
    for (let i = 0; i < Math.max(tta.length, ttb.length); i++) {
      if (tta[i] === undefined) return -1;
      if (ttb[i] === undefined) return 1;
      if (tta[i] < ttb[i]) return -1;
      if (tta[i] > ttb[i]) return 1;
    }
    return 0;
  });
  
  // 3. Xác định Level và Trạng thái Cha (hasChildren) cho từng bản ghi
  const projectsWithWbs = sortedProjs.map((item, idx) => {
    const ttStr = String(item.tt || "").trim();
    let level = 1;
    if (ttStr.includes(".")) {
      const parts = ttStr.split(".");
      level = parts.length;
    }
    
    let hasChildren = false;
    for (let i = 0; i < sortedProjs.length; i++) {
      const otherTt = String(sortedProjs[i].tt || "").trim();
      if (otherTt !== ttStr && otherTt.startsWith(ttStr + ".")) {
        hasChildren = true;
        break;
      }
    }
    
    return {
      ...item,
      wbsLevel: level,
      hasChildren: hasChildren
    };
  });
  
  document.getElementById("masterTableCount").textContent = `Hiển thị: ${filteredRaw.length} / ${state.master.length} gói thầu`;
  
  if (projectsWithWbs.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="44" class="table-empty-state">
          <div class="table-empty-icon"><i class="fa-solid fa-folder-open"></i></div>
          Không tìm thấy gói thầu nào khớp với bộ lọc tìm kiếm.
        </td>
      </tr>
    `;
    return;
  }
  
  projectsWithWbs.forEach(r => {
    const level = r.wbsLevel;
    const isWbs = r.hasChildren;
    const ttStr = String(r.tt || "").trim();
    const pkg = r.goiThauPl || "";
    const basePkg = pkg.split('.')[0];
    
    // Ràng buộc hiển thị theo "Cấp công trình" vs "Cấp chi tiết"
    let rowStyle = "";
    if (currentMasterViewLevel === "project" && level > 1) {
      rowStyle = "display: none;";
    }
    
    // CSS classes cho dòng
    let trClass = "";
    if (level === 1) {
      trClass = "wbs-row-style";
    } else if (level === 2) {
      trClass = `child-row-${basePkg}-cdt wbs-level2-row`;
    } else {
      const parentPrefix = ttStr.substring(0, ttStr.lastIndexOf('.')).replace(/\./g, '_');
      trClass = `child-row-level3-${parentPrefix}-cdt child-row-${basePkg}-cdt wbs-level3-row`;
    }
    
    const tr = document.createElement("tr");
    tr.className = trClass;
    if (rowStyle) tr.style.cssText = rowStyle;
    
    tr.setAttribute("data-tt", ttStr);
    tr.setAttribute("data-level", level);
    tr.setAttribute("data-parent", basePkg);
    
    const badgeDkDu = r.dieuKienDu === "ĐỦ ĐIỀU KIỆN KHỞI CÔNG" ? "badge-success" : "badge-danger";
    let badgeBuTienDo = "badge-muted";
    if (r.buTienDo === "Đang chạy") badgeBuTienDo = "badge-info";
    else if (r.buTienDo === "Chậm tiến độ") badgeBuTienDo = "badge-danger";
    
    const getWeekBadge = (val) => {
      if (val === "Đạt") return "badge-success";
      if (val === "Chậm") return "badge-danger";
      if (val === "Cần hỗ trợ") return "badge-warning";
      return "badge-muted";
    };
    
    // Thiết kế cột Hạng mục với nút Toggle và thụt lề
    let hangMucHtml = "";
    const paddingLeftVal = (level - 1) * 20;
    const indentSymbol = level > 1 ? '<span style="color: var(--text-muted); margin-right: 6px; font-weight: bold;">└─</span>' : '';
    
    if (isWbs) {
      const btnSymbol = "—";
      const clickAction = level === 1 ? `toggleLevel1JS('${ttStr}')` : `toggleLevel2JS('${ttStr}')`;
      const btnId = `btn-toggle-${ttStr.replace(/\./g, '_')}-cdt`;
      
      hangMucHtml = `
        <div style="padding-left: ${paddingLeftVal}px; display: flex; align-items: center;">
          ${indentSymbol}
          <span id="${btnId}" class="toggle-btn" onclick="${clickAction}">${btnSymbol}</span>
          <b style="${level === 1 ? 'color: #1e3a8a; font-size: 0.82rem;' : ''}">${r.hangMuc}</b>
        </div>
      `;
    } else {
      hangMucHtml = `
        <div style="padding-left: ${paddingLeftVal}px; display: flex; align-items: center;">
          ${indentSymbol}
          <span style="color: var(--text-main); ${level === 1 ? 'font-weight: 700;' : ''}">${r.hangMuc}</span>
        </div>
      `;
    }
    
    const isLevel1ParentEmpty = (level === 1 && isWbs && !r.maBsc);
    
    tr.innerHTML = `
      <td class="sticky-col-1" style="font-weight: 700; color: var(--primary); text-align: center;">${r.maBsc || (level === 1 ? r.tt : '—')}</td>
      <td class="sticky-col-2" title="${r.hangMuc}">${hangMucHtml}</td>
      <td class="sticky-col-3">${r.goiThauPl || '—'}</td>
      <td class="sticky-col-4">${r.nhomCt || '—'}</td>
      <td class="sticky-col-5">${r.phuTrach || '—'}</td>
      <td style="font-weight: 700;">${formatNumberSafe(r.nganSach, 2, isLevel1ParentEmpty ? '' : '0.00')}</td>
      <td style="font-weight: 700;">${formatNumberSafe(r.giaTriHdcu, 2, isLevel1ParentEmpty ? '' : '0.00')}</td>
      <td style="font-weight: 600;">${r.tileHdcuNs ? formatNumberSafe(r.tileHdcuNs, 1, '0.0') + '%' : (isLevel1ParentEmpty ? '' : '0.0%')}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${badgeDkDu}">${r.dieuKienDu}</span>`}</td>
      <td>${isLevel1ParentEmpty ? '' : formatDate(r.ngayBdKhoiCong)}</td>
      <td style="font-weight: 700;">${formatNumberSafe(r.luyKeGiaTriHdAB, 2, isLevel1ParentEmpty ? '' : '0.00')}</td>
      <td style="font-weight: 700; color: ${r.luyKePhatSinhBB > 0 ? 'var(--warning)' : 'inherit'};">
        ${formatNumberSafe(r.luyKePhatSinhBB, 2, isLevel1ParentEmpty ? '' : '0.00')}
      </td>
      <td style="font-weight: 800; color: var(--primary);">${formatNumberSafe(r.luyKeTongChiPhi, 2, isLevel1ParentEmpty ? '' : '0.00')}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${badgeBuTienDo}">${r.buTienDo}</span>`}</td>
      
      <td>${r.ttHstktc || ''}</td>
      <td>${r.ttSpecs || ''}</td>
      <td>${r.ttBoq || ''}</td>
      <td>${formatDate(r.ngayBdYc)}</td>
      <td>${formatDate(r.ngayKtYc)}</td>
      <td>${r.ttLcnt || ''}</td>
      <td>${r.ttHdcu || ''}</td>
      <td>${r.ttKhcu || ''}</td>
      <td>${r.ttKhtk || ''}</td>
      
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${r.dk1 === 'Đạt' ? 'badge-success' : 'badge-danger'}">${r.dk1 || 'Chưa đạt'}</span>`}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${r.dk2 === 'Đạt' ? 'badge-success' : 'badge-danger'}">${r.dk2 || 'Chưa đạt'}</span>`}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${r.dk3 === 'Đạt' ? 'badge-success' : 'badge-danger'}">${r.dk3 || 'Chưa đạt'}</span>`}</td>
      
      <td title="${r.hsTienKc || ''}">${r.hsTienKc || ''}</td>
      <td style="font-weight: 600; text-align:center;">${r.taiLieuKhThang || ''}</td>
      <td style="text-align: center; font-weight: 700; color: ${r.phatSinhChuaDuyet > 0 ? 'var(--warning)' : 'inherit'};">${r.phatSinhChuaDuyet || (isLevel1ParentEmpty ? '' : '0')}</td>
      <td style="text-align: center; font-weight: 700; color: ${r.cungUngChuaDuyet > 0 ? 'var(--warning)' : 'inherit'};">${r.cungUngChuaDuyet || (isLevel1ParentEmpty ? '' : '0')}</td>
      
      <td>${r.t1Kh || '—'}</td>
      <td>${r.t1Kq || '—'}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${getWeekBadge(r.t1Dg)}">${r.t1Dg || '—'}</span>`}</td>
      <td>${r.t2Kh || '—'}</td>
      <td>${r.t2Kq || '—'}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${getWeekBadge(r.t2Dg)}">${r.t2Dg || '—'}</span>`}</td>
      <td>${r.t3Kh || '—'}</td>
      <td>${r.t3Kq || '—'}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${getWeekBadge(r.t3Dg)}">${r.t3Dg || '—'}</span>`}</td>
      <td>${r.t4Kh || '—'}</td>
      <td>${r.t4Kq || '—'}</td>
      <td>${isLevel1ParentEmpty ? '' : `<span class="badge ${getWeekBadge(r.t4Dg)}">${r.t4Dg || '—'}</span>`}</td>
      
      <td style="text-align: center;">
        ${isLevel1ParentEmpty ? '' : `
        <div class="row-actions">
          <button class="action-btn-icon ai-btn" onclick="analyzeRowWithAi('${r.maBsc}')" title="Phân tích AI"><i class="fa-solid fa-wand-magic-sparkles"></i></button>
          <button class="action-btn-icon edit-btn" onclick="editMasterRow('${r.maBsc}')" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteMasterRow('${r.maBsc}')" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
        `}
      </td>
    `;
    tbody.appendChild(tr);
  });
  applyMasterColumnVisibility();
}

// 5.2. Render Sổ 01 - Hồ sơ tiền khởi công
function renderSo01Table() {
  const searchVal = document.getElementById("so01SearchInput").value.toLowerCase().trim();
  const filterBsc = document.getElementById("so01FilterBsc").value;
  const filterStatus = document.getElementById("so01FilterStatus").value;
  
  const tbody = document.getElementById("so01TableBody");
  tbody.innerHTML = "";
  
  const filtered = state.so01.filter(r => {
    const searchMatch = !searchVal ||
                        (r.tenSpham && r.tenSpham.toLowerCase().includes(searchVal)) ||
                        (r.loaiHoSo && r.loaiHoSo.toLowerCase().includes(searchVal));
    const bscMatch = !filterBsc || r.maBsc === filterBsc;
    const statusMatch = !filterStatus || r.ttDuyet === filterStatus;
    
    return searchMatch && bscMatch && statusMatch;
  });
  
  document.getElementById("so01TableCount").textContent = `Hiển thị: ${filtered.length} / ${state.so01.length} bản ghi`;
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="table-empty-state">Không có hồ sơ nào.</td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((r, idx) => {
    let statusClass = "badge-muted";
    if (r.ttDuyet === "Đã duyệt") statusClass = "badge-success";
    else if (r.ttDuyet === "Đang trình duyệt") statusClass = "badge-info";
    else if (r.ttDuyet === "Yêu cầu chỉnh sửa") statusClass = "badge-danger";
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.maBsc}</td>
      <td style="font-weight: 500;">${r.hangMuc}</td>
      <td><strong>${r.loaiHoSo}</strong></td>
      <td>${r.tenSpham}</td>
      <td><a href="${r.linkLuuTru}" target="_blank" title="Mở đường dẫn"><i class="fa-solid fa-arrow-up-right-from-square"></i> Tài liệu</a></td>
      <td>${formatDate(r.ngayHt)}</td>
      <td>${r.nguoiLap || '—'}</td>
      <td>${r.nguoiDuyet || '—'}</td>
      <td><span class="badge ${statusClass}">${r.ttDuyet}</span></td>
      <td>
        <div class="row-actions" style="justify-content: center;">
          <button class="action-btn-icon edit-btn" onclick="editSo01Row(${idx})" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteSo01Row(${idx})" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 5.3. Render Sổ 02 - Kế hoạch triển khai
function renderSo02Table() {
  const searchVal = document.getElementById("so02SearchInput").value.toLowerCase().trim();
  const filterBsc = document.getElementById("so02FilterBsc").value;
  const filterYckt = document.getElementById("so02FilterYckt").value;
  const filterStatus = document.getElementById("so02FilterStatus").value;
  
  const tbody = document.getElementById("so02TableBody");
  tbody.innerHTML = "";
  
  const filtered = state.so02.filter(r => {
    const searchMatch = !searchVal || (r.noiDungChinh && r.noiDungChinh.toLowerCase().includes(searchVal));
    const bscMatch = !filterBsc || r.maBsc === filterBsc;
    const ycktMatch = !filterYckt || r.datYckt === filterYckt;
    const statusMatch = !filterStatus || r.ttDuyet === filterStatus;
    
    return searchMatch && bscMatch && ycktMatch && statusMatch;
  });
  
  document.getElementById("so02TableCount").textContent = `Hiển thị: ${filtered.length} / ${state.so02.length} bản ghi`;
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="14" class="table-empty-state">Không có kế hoạch triển khai nào.</td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((r, idx) => {
    let statusClass = "badge-muted";
    if (r.ttDuyet === "Đã duyệt") statusClass = "badge-success";
    else if (r.ttDuyet === "Chờ duyệt") statusClass = "badge-warning";
    else if (r.ttDuyet === "Từ chối") statusClass = "badge-danger";
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.maBsc}</td>
      <td style="font-weight: 500;">${r.hangMuc}</td>
      <td><strong>${r.thang}</strong></td>
      <td>${r.loaiTaiLieu}</td>
      <td title="${r.noiDungChinh}">${r.noiDungChinh}</td>
      <td><span class="badge ${r.datYckt === 'Đạt' ? 'badge-success' : 'badge-danger'}">${r.datYckt}</span></td>
      <td><a href="${r.linkTaiLieu}" target="_blank"><i class="fa-solid fa-link"></i> Link</a></td>
      <td>${r.ttLap}</td>
      <td><span class="badge ${statusClass}">${r.ttDuyet}</span></td>
      <td>${r.nguoiLap || '—'}</td>
      <td>${r.nguoiDuyet || '—'}</td>
      <td>${formatDate(r.ngayDuyet)}</td>
      <td>
        <div class="row-actions" style="justify-content: center;">
          <button class="action-btn-icon edit-btn" onclick="editSo02Row(${idx})" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteSo02Row(${idx})" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 5.4. Render Sổ 03 - Phát sinh hồ sơ HĐ B-B'
function renderSo03Table() {
  const searchVal = document.getElementById("so03SearchInput").value.toLowerCase().trim();
  const filterBsc = document.getElementById("so03FilterBsc").value;
  const filterLoai = document.getElementById("so03FilterLoai").value;
  const filterStatus = document.getElementById("so03FilterStatus").value;
  
  const tbody = document.getElementById("so03TableBody");
  tbody.innerHTML = "";
  
  const filtered = state.so03.filter(r => {
    const searchMatch = !searchVal || 
                        (r.moTa && r.moTa.toLowerCase().includes(searchVal)) ||
                        (r.nguyenNhan && r.nguyenNhan.toLowerCase().includes(searchVal)) ||
                        (r.maPs && r.maPs.toLowerCase().includes(searchVal));
    const bscMatch = !filterBsc || r.maBsc === filterBsc;
    const loaiMatch = !filterLoai || r.loai === filterLoai;
    const statusMatch = !filterStatus || r.ttDuyet === filterStatus;
    
    return searchMatch && bscMatch && loaiMatch && statusMatch;
  });
  
  document.getElementById("so03TableCount").textContent = `Hiển thị: ${filtered.length} / ${state.so03.length} bản ghi`;
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="16" class="table-empty-state">Không có tài liệu phát sinh nào.</td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((r, idx) => {
    let statusClass = "badge-muted";
    if (r.ttDuyet === "Đã duyệt") statusClass = "badge-success";
    else if (r.ttDuyet === "Chờ duyệt") statusClass = "badge-warning";
    else if (r.ttDuyet === "Không duyệt") statusClass = "badge-danger";
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="font-weight: 700; color: var(--warning);">${r.maPs}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.maBsc}</td>
      <td style="font-weight: 500;">${r.hangMuc}</td>
      <td>${formatDate(r.ngayPs)}</td>
      <td><strong>${r.loai}</strong></td>
      <td style="font-weight: 700; color: var(--danger);">${r.giaTri ? r.giaTri.toFixed(3) : '0.000'}</td>
      <td style="font-weight: 600; text-align: center;">+${r.anhHuongTd || 0} ngày</td>
      <td title="${r.moTa}">${r.moTa}</td>
      <td title="${r.nguyenNhan}">${r.nguyenNhan}</td>
      <td title="${r.deXuat}">${r.deXuat}</td>
      <td><span class="badge ${statusClass}">${r.ttDuyet}</span></td>
      <td>${r.nguoiDuyet || '—'}</td>
      <td>${formatDate(r.ngayDuyet)}</td>
      <td><a href="${r.linkHoSo}" target="_blank"><i class="fa-solid fa-file-pdf"></i> Tài liệu</a></td>
      <td title="${r.noiDungDieuChinh}">${r.noiDungDieuChinh || '—'}</td>
      <td>
        <div class="row-actions" style="justify-content: center;">
          <button class="action-btn-icon edit-btn" onclick="editSo03Row(${idx})" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteSo03Row(${idx})" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 5.5. Render Sổ 04 - Yêu cầu cung ứng đặc thù
function renderSo04Table() {
  const searchVal = document.getElementById("so04SearchInput").value.toLowerCase().trim();
  const filterBsc = document.getElementById("so04FilterBsc").value;
  const filterLoai = document.getElementById("so04FilterLoaiYc").value;
  const filterStatus = document.getElementById("so04FilterStatus").value;
  
  const tbody = document.getElementById("so04TableBody");
  tbody.innerHTML = "";
  
  const filtered = state.so04.filter(r => {
    const searchMatch = !searchVal || 
                        (r.vatTu && r.vatTu.toLowerCase().includes(searchVal)) ||
                        (r.dacTa && r.dacTa.toLowerCase().includes(searchVal)) ||
                        (r.maYc && r.maYc.toLowerCase().includes(searchVal));
    const bscMatch = !filterBsc || r.maBsc === filterBsc;
    const loaiMatch = !filterLoai || r.loaiYc === filterLoai;
    const statusMatch = !filterStatus || r.ttDuyet === filterStatus;
    
    return searchMatch && bscMatch && loaiMatch && statusMatch;
  });
  
  document.getElementById("so04TableCount").textContent = `Hiển thị: ${filtered.length} / ${state.so04.length} bản ghi`;
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="16" class="table-empty-state">Không có yêu cầu cung ứng nào.</td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((r, idx) => {
    let statusClass = "badge-muted";
    if (r.ttDuyet === "Đã duyệt") statusClass = "badge-success";
    else if (r.ttDuyet === "Chờ duyệt") statusClass = "badge-warning";
    else if (r.ttDuyet === "Từ chối") statusClass = "badge-danger";
    
    let supplyClass = "badge-muted";
    if (r.ttCungUng === "Đã bàn giao công trường") supplyClass = "badge-success";
    else if (r.ttCungUng === "Đang mua") supplyClass = "badge-info";
    else if (r.ttCungUng === "Chưa mua") supplyClass = "badge-danger";
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="font-weight: 700; color: var(--primary);">${r.maYc}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.maBsc}</td>
      <td style="font-weight: 500;">${r.hangMuc}</td>
      <td>${formatDate(r.ngayYc)}</td>
      <td><strong>${r.loaiYc}</strong></td>
      <td><strong>${r.vatTu}</strong></td>
      <td title="${r.dacTa}">${r.dacTa}</td>
      <td>${r.kl}</td>
      <td>${r.dvt}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.giaTri ? r.giaTri.toFixed(3) : '0.000'}</td>
      <td>${r.trongNgoaiHd}</td>
      <td>${formatDate(r.ngayCan)}</td>
      <td><span class="badge ${statusClass}">${r.ttDuyet}</span></td>
      <td><span class="badge ${supplyClass}">${r.ttCungUng}</span></td>
      <td><a href="${r.linkHoSo}" target="_blank"><i class="fa-solid fa-paperclip"></i> File</a></td>
      <td>
        <div class="row-actions" style="justify-content: center;">
          <button class="action-btn-icon edit-btn" onclick="editSo04Row(${idx})" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteSo04Row(${idx})" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 5.6. Render Sổ 05 - Bù tiến độ thi công
function renderSo05Table() {
  const searchVal = document.getElementById("so05SearchInput").value.toLowerCase().trim();
  const filterBsc = document.getElementById("so05FilterBsc").value;
  const filterStatus = document.getElementById("so05FilterStatus").value;
  
  const tbody = document.getElementById("so05TableBody");
  tbody.innerHTML = "";
  
  const filtered = state.so05.filter(r => {
    const searchMatch = !searchVal || 
                        (r.nguyenNhan && r.nguyenNhan.toLowerCase().includes(searchVal)) ||
                        (r.giaiPhapBu && r.giaiPhapBu.toLowerCase().includes(searchVal)) ||
                        (r.chiTietGiaiPhap && r.chiTietGiaiPhap.toLowerCase().includes(searchVal));
    const bscMatch = !filterBsc || r.maBsc === filterBsc;
    const statusMatch = !filterStatus || r.ttThucHien === filterStatus;
    
    return searchMatch && bscMatch && statusMatch;
  });
  
  document.getElementById("so05TableCount").textContent = `Hiển thị: ${filtered.length} / ${state.so05.length} bản ghi`;
  
  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="14" class="table-empty-state">Không có bản ghi bù tiến độ nào.</td>
      </tr>
    `;
    return;
  }
  
  filtered.forEach((r, idx) => {
    let actionClass = "badge-muted";
    if (r.ttThucHien === "Đã bắt kịp tiến độ") actionClass = "badge-success";
    else if (r.ttThucHien === "Đang triển khai bù") actionClass = "badge-info";
    else if (r.ttThucHien === "Thất bại") actionClass = "badge-danger";
    
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${idx + 1}</td>
      <td style="font-weight: 700; color: var(--primary);">${r.maBsc}</td>
      <td style="font-weight: 500;">${r.hangMuc}</td>
      <td>${formatDate(r.ngayPhatHien)}</td>
      <td style="font-weight: 700; color: var(--danger); text-align: center;">${r.mucCham} ngày</td>
      <td><strong>${formatDate(r.mocCamKet)}</strong></td>
      <td title="${r.nguyenNhan}">${r.nguyenNhan}</td>
      <td><strong>${r.giaiPhapBu}</strong></td>
      <td title="${r.chiTietGiaiPhap}">${r.chiTietGiaiPhap}</td>
      <td title="${r.kqThucHienBu}">${r.kqThucHienBu || '—'}</td>
      <td><span class="badge ${r.ttDuyet.includes('Đã phê duyệt') ? 'badge-success' : 'badge-warning'}">${r.ttDuyet}</span></td>
      <td><span class="badge ${actionClass}">${r.ttThucHien}</span></td>
      <td><a href="${r.linkPhuongAn}" target="_blank"><i class="fa-solid fa-file-signature"></i> Phương án</a></td>
      <td>
        <div class="row-actions" style="justify-content: center;">
          <button class="action-btn-icon edit-btn" onclick="editSo05Row(${idx})" title="Chỉnh sửa"><i class="fa-solid fa-pen-to-square"></i></button>
          <button class="action-btn-icon delete-btn" onclick="deleteSo05Row(${idx})" title="Xóa"><i class="fa-solid fa-trash-can"></i></button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

// 6. ĐÓNG MỞ MODALS TƯƠNG ỨNG TỪNG FORM
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("active");
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove("active");
  }
}

function openModalForTab(tabName) {
  // Đổ dữ liệu BSC vào các Form select trước khi mở
  if (tabName !== "master" && tabName !== "dashboard") {
    populateBscDropdown(`${tabName}MaBsc`);
  }
  
  switch (tabName) {
    case "master":
      document.getElementById("formMaster").reset();
      document.getElementById("masterIndex").value = "";
      document.getElementById("masterMaBsc").removeAttribute("readonly");
      document.getElementById("modalMasterTitle").textContent = "Thêm Gói thầu Master mới";
      openModal("modalMaster");
      break;
    case "so01":
      document.getElementById("formSo01").reset();
      document.getElementById("so01Index").value = "";
      document.getElementById("modalSo01Title").textContent = "Thêm Hồ sơ Tiền Khởi Công";
      openModal("modalSo01");
      break;
    case "so02":
      document.getElementById("formSo02").reset();
      document.getElementById("so02Index").value = "";
      document.getElementById("modalSo02Title").textContent = "Thêm Kế hoạch triển khai Tháng/Tuần";
      openModal("modalSo02");
      break;
    case "so03":
      document.getElementById("formSo03").reset();
      document.getElementById("so03Index").value = "";
      document.getElementById("modalSo03Title").textContent = "Thêm phát sinh HĐ B - B'";
      // Tạo mã phát sinh tự động dạng PS-xxx
      document.getElementById("so03MaPs").value = generateNextAutoCode("so03", "maPs", "PS-");
      openModal("modalSo03");
      break;
    case "so04":
      document.getElementById("formSo04").reset();
      document.getElementById("so04Index").value = "";
      document.getElementById("modalSo04Title").textContent = "Yêu cầu cung ứng đặc thù mới";
      // Tạo mã yêu cầu tự động dạng YC-xxx
      document.getElementById("so04MaYc").value = generateNextAutoCode("so04", "maYc", "YC-");
      openModal("modalSo04");
      break;
    case "so05":
      document.getElementById("formSo05").reset();
      document.getElementById("so05Index").value = "";
      document.getElementById("modalSo05Title").textContent = "Lập phương án bù tiến độ thi công";
      openModal("modalSo05");
      break;
  }
}

// Sinh mã tự tăng (Ví dụ: PS-004, YC-004)
function generateNextAutoCode(slipKey, codeField, prefix) {
  let maxNum = 0;
  state[slipKey].forEach(item => {
    const val = item[codeField] || "";
    if (val.startsWith(prefix)) {
      const numPart = parseInt(val.substring(prefix.length)) || 0;
      if (numPart > maxNum) {
        maxNum = numPart;
      }
    }
  });
  const nextNum = maxNum + 1;
  return prefix + String(nextNum).padStart(3, '0');
}

// 7. XỬ LÝ LƯU (SAVE) VÀ CHỈNH SỬA (EDIT) DỮ LIỆU TỪ FORM

// 7.1. BẢNG MASTER
function saveMasterForm(e) {
  e.preventDefault();
  const form = document.getElementById("formMaster");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("masterIndex").value;
  const maBsc = document.getElementById("masterMaBsc").value.toUpperCase().trim();
  
  // Kiểm tra trùng Mã BSC khi thêm mới
  if (idxVal === "") {
    const duplicate = state.master.some(m => m.maBsc === maBsc);
    if (duplicate) {
      alert(`Mã BSC "${maBsc}" đã tồn tại trên hệ thống. Vui lòng nhập mã khác!`);
      return;
    }
  }
  
  const data = {
    maBsc: maBsc,
    nhomCt: document.getElementById("masterNhomCt").value,
    goiThauPl: document.getElementById("masterGoiThauPl").value,
    hangMuc: document.getElementById("masterHangMuc").value.trim(),
    phuTrach: document.getElementById("masterPhuTrach").value.trim(),
    nganSach: parseFloat(document.getElementById("masterNganSach").value) || 0,
    giaTriHdcu: parseFloat(document.getElementById("masterGiaTriHdcu").value) || 0,
    ngayBdYc: document.getElementById("masterNgayBdYc").value,
    ngayKtYc: document.getElementById("masterNgayKtYc").value,
    khHstktc: document.getElementById("masterKhHstktc").value,
    ttHstktc: document.getElementById("masterTtHstktc").value,
    ttSpecs: document.getElementById("masterTtSpecs").value,
    ttBoq: document.getElementById("masterTtBoq").value,
    khLcnt: document.getElementById("masterKhLcnt").value,
    ttLcnt: document.getElementById("masterTtLcnt").value,
    khHdcu: document.getElementById("masterKhHdcu").value,
    ttHdcu: document.getElementById("masterTtHdcu").value,
    khPdKhcu: document.getElementById("masterKhPdKhcu").value,
    ttKhcu: document.getElementById("masterTtKhcu").value,
    khPlhdCdt: document.getElementById("masterKhPlhdCdt").value,
    ttPlhdCdt: document.getElementById("masterTtPlhdCdt").value,
    khPdKhtk: document.getElementById("masterKhPdKhtk").value,
    ttKhtk: document.getElementById("masterTtKhtk").value,
    ngayBdKhoiCong: document.getElementById("masterNgayBdKhoiCong").value,
    luyKeGiaTriHdAB: parseFloat(document.getElementById("masterLuyKeGiaTriHdAB").value) || 0,
    dk1: document.getElementById("masterDk1").value,
    dk2: document.getElementById("masterDk2").value,
    dk3: document.getElementById("masterDk3").value,
    khQaQc: document.getElementById("masterKhQaQc").value.trim(),
    kqQaQc: document.getElementById("masterKqQaQc").value.trim(),
    dgQaQc: document.getElementById("masterDgQaQc").value.trim(),
    khThiCong: document.getElementById("masterKhThiCong").value.trim(),
    kqThiCong: document.getElementById("masterKqThiCong").value.trim(),
    dgThiCong: document.getElementById("masterDgThiCong").value.trim(),
    buTienDo: document.getElementById("masterBuTienDo").value,
    t1Kh: document.getElementById("masterT1Kh").value.trim(),
    t1Kq: document.getElementById("masterT1Kq").value.trim(),
    t1Dg: document.getElementById("masterT1Dg").value,
    t2Kh: document.getElementById("masterT2Kh").value.trim(),
    t2Kq: document.getElementById("masterT2Kq").value.trim(),
    t2Dg: document.getElementById("masterT2Dg").value,
    t3Kh: document.getElementById("masterT3Kh").value.trim(),
    t3Kq: document.getElementById("masterT3Kq").value.trim(),
    t3Dg: document.getElementById("masterT3Dg").value,
    t4Kh: document.getElementById("masterT4Kh").value.trim(),
    t4Kq: document.getElementById("masterT4Kq").value.trim(),
    t4Dg: document.getElementById("masterT4Dg").value
  };
  
  if (idxVal === "") {
    // Thêm mới
    state.master.push(data);
  } else {
    // Cập nhật
    const index = parseInt(idxVal);
    state.master[index] = data;
  }
  
  closeModal("modalMaster");
  saveStateToStorage(true);
}

window.editMasterRow = function(maBsc) {
  const index = state.master.findIndex(m => m.maBsc === maBsc);
  if (index === -1) return;
  
  const r = state.master[index];
  
  document.getElementById("masterIndex").value = index;
  document.getElementById("masterMaBsc").value = r.maBsc;
  document.getElementById("masterMaBsc").setAttribute("readonly", "true"); // Khóa chính không cho sửa trực tiếp tránh sai lệch
  
  document.getElementById("masterNhomCt").value = r.nhomCt || "Dự án VSV-A";
  document.getElementById("masterGoiThauPl").value = r.goiThauPl || "Xây dựng";
  document.getElementById("masterHangMuc").value = r.hangMuc || "";
  document.getElementById("masterPhuTrach").value = r.phuTrach || "";
  document.getElementById("masterNganSach").value = r.nganSach || "";
  document.getElementById("masterGiaTriHdcu").value = r.giaTriHdcu || "";
  document.getElementById("masterNgayBdYc").value = r.ngayBdYc || "";
  document.getElementById("masterNgayKtYc").value = r.ngayKtYc || "";
  document.getElementById("masterKhHstktc").value = r.khHstktc || "";
  document.getElementById("masterTtHstktc").value = r.ttHstktc || "Chưa phát hành";
  document.getElementById("masterTtSpecs").value = r.ttSpecs || "Chưa có";
  document.getElementById("masterTtBoq").value = r.ttBoq || "Chưa có";
  document.getElementById("masterKhLcnt").value = r.khLcnt || "";
  document.getElementById("masterTtLcnt").value = r.ttLcnt || "Chưa triển khai";
  document.getElementById("masterKhHdcu").value = r.khHdcu || "";
  document.getElementById("masterTtHdcu").value = r.ttHdcu || "Chưa ký";
  document.getElementById("masterKhPdKhcu").value = r.khPdKhcu || "";
  document.getElementById("masterTtKhcu").value = r.ttKhcu || "Chưa lập";
  document.getElementById("masterKhPlhdCdt").value = r.khPlhdCdt || "";
  document.getElementById("masterTtPlhdCdt").value = r.ttPlhdCdt || "Chưa ký";
  document.getElementById("masterKhPdKhtk").value = r.khPdKhtk || "";
  document.getElementById("masterTtKhtk").value = r.ttKhtk || "Chưa lập";
  document.getElementById("masterNgayBdKhoiCong").value = r.ngayBdKhoiCong || "";
  document.getElementById("masterLuyKeGiaTriHdAB").value = r.luyKeGiaTriHdAB || "";
  
  document.getElementById("masterDk1").value = r.dk1 || "Chưa đạt";
  document.getElementById("masterDk2").value = r.dk2 || "Chưa đạt";
  document.getElementById("masterDk3").value = r.dk3 || "Chưa đạt";
  
  document.getElementById("masterKhQaQc").value = r.khQaQc || "";
  document.getElementById("masterKqQaQc").value = r.kqQaQc || "";
  document.getElementById("masterDgQaQc").value = r.dgQaQc || "";
  document.getElementById("masterKhThiCong").value = r.khThiCong || "";
  document.getElementById("masterKqThiCong").value = r.kqThiCong || "";
  document.getElementById("masterDgThiCong").value = r.dgThiCong || "";
  document.getElementById("masterBuTienDo").value = r.buTienDo || "Không chạy";
  
  document.getElementById("masterT1Kh").value = r.t1Kh || "";
  document.getElementById("masterT1Kq").value = r.t1Kq || "";
  document.getElementById("masterT1Dg").value = r.t1Dg || "";
  document.getElementById("masterT2Kh").value = r.t2Kh || "";
  document.getElementById("masterT2Kq").value = r.t2Kq || "";
  document.getElementById("masterT2Dg").value = r.t2Dg || "";
  document.getElementById("masterT3Kh").value = r.t3Kh || "";
  document.getElementById("masterT3Kq").value = r.t3Kq || "";
  document.getElementById("masterT3Dg").value = r.t3Dg || "";
  document.getElementById("masterT4Kh").value = r.t4Kh || "";
  document.getElementById("masterT4Kq").value = r.t4Kq || "";
  document.getElementById("masterT4Dg").value = r.t4Dg || "";
  
  document.getElementById("modalMasterTitle").textContent = "Cập nhật Gói thầu Master - " + r.maBsc;
  openModal("modalMaster");
};

window.deleteMasterRow = function(maBsc) {
  if (confirm(`Bạn có chắc chắn muốn xóa gói thầu "${maBsc}" không? Lưu ý: Việc này có thể làm ảnh hưởng đến tính liên kết dữ liệu trong các sổ phụ.`)) {
    state.master = state.master.filter(m => m.maBsc !== maBsc);
    saveStateToStorage(true);
  }
};

// 7.2. SỔ 01 - HỒ SƠ TIỀN KHỞI CÔNG
function saveSo01Form(e) {
  e.preventDefault();
  const form = document.getElementById("formSo01");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("so01Index").value;
  const maBsc = document.getElementById("so01MaBsc").value;
  
  const data = {
    maBsc: maBsc,
    hangMuc: getHangMucByMaBsc(maBsc),
    loaiHoSo: document.getElementById("so01LoaiHoSo").value,
    tenSpham: document.getElementById("so01TenSpham").value.trim(),
    linkLuuTru: document.getElementById("so01LinkLuuTru").value.trim(),
    ngayHt: document.getElementById("so01NgayHt").value,
    ttDuyet: document.getElementById("so01TtDuyet").value,
    nguoiLap: document.getElementById("so01NguoiLap").value.trim(),
    nguoiDuyet: document.getElementById("so01NguoiDuyet").value.trim()
  };
  
  if (idxVal === "") {
    state.so01.push(data);
  } else {
    const index = parseInt(idxVal);
    state.so01[index] = data;
  }
  
  closeModal("modalSo01");
  saveStateToStorage(true);
}

window.editSo01Row = function(index) {
  const r = state.so01[index];
  if (!r) return;
  
  populateBscDropdown("so01MaBsc", r.maBsc);
  
  document.getElementById("so01Index").value = index;
  document.getElementById("so01HangMuc").value = r.hangMuc;
  document.getElementById("so01LoaiHoSo").value = r.loaiHoSo;
  document.getElementById("so01TenSpham").value = r.tenSpham;
  document.getElementById("so01LinkLuuTru").value = r.linkLuuTru;
  document.getElementById("so01NgayHt").value = r.ngayHt;
  document.getElementById("so01TtDuyet").value = r.ttDuyet;
  document.getElementById("so01NguoiLap").value = r.nguoiLap || "";
  document.getElementById("so01NguoiDuyet").value = r.nguoiDuyet || "";
  
  document.getElementById("modalSo01Title").textContent = "Cập nhật Hồ sơ Tiền Khởi Công";
  openModal("modalSo01");
};

window.deleteSo01Row = function(index) {
  if (confirm("Bạn có chắc chắn muốn xóa hồ sơ khởi công này không?")) {
    state.so01.splice(index, 1);
    saveStateToStorage(true);
  }
};

// 7.3. SỔ 02 - KẾ HOẠCH TRIỂN KHAI
function saveSo02Form(e) {
  e.preventDefault();
  const form = document.getElementById("formSo02");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("so02Index").value;
  const maBsc = document.getElementById("so02MaBsc").value;
  
  const data = {
    maBsc: maBsc,
    hangMuc: getHangMucByMaBsc(maBsc),
    thang: document.getElementById("so02Thang").value.trim(),
    loaiTaiLieu: document.getElementById("so02LoaiTaiLieu").value,
    noiDungChinh: document.getElementById("so02NoiDungChinh").value.trim(),
    datYckt: document.getElementById("so02DatYckt").value,
    linkTaiLieu: document.getElementById("so02LinkTaiLieu").value.trim(),
    ttLap: document.getElementById("so02TtLap").value,
    ttDuyet: document.getElementById("so02TtDuyet").value,
    nguoiLap: document.getElementById("so02NguoiLap").value.trim(),
    nguoiDuyet: document.getElementById("so02NguoiDuyet").value.trim(),
    ngayDuyet: document.getElementById("so02NgayDuyet").value
  };
  
  if (idxVal === "") {
    state.so02.push(data);
  } else {
    const index = parseInt(idxVal);
    state.so02[index] = data;
  }
  
  closeModal("modalSo02");
  saveStateToStorage(true);
}

window.editSo02Row = function(index) {
  const r = state.so02[index];
  if (!r) return;
  
  populateBscDropdown("so02MaBsc", r.maBsc);
  
  document.getElementById("so02Index").value = index;
  document.getElementById("so02HangMuc").value = r.hangMuc;
  document.getElementById("so02Thang").value = r.thang;
  document.getElementById("so02LoaiTaiLieu").value = r.loaiTaiLieu;
  document.getElementById("so02NoiDungChinh").value = r.noiDungChinh;
  document.getElementById("so02DatYckt").value = r.datYckt;
  document.getElementById("so02LinkTaiLieu").value = r.linkTaiLieu;
  document.getElementById("so02TtLap").value = r.ttLap;
  document.getElementById("so02TtDuyet").value = r.ttDuyet;
  document.getElementById("so02NguoiLap").value = r.nguoiLap || "";
  document.getElementById("so02NguoiDuyet").value = r.nguoiDuyet || "";
  document.getElementById("so02NgayDuyet").value = r.ngayDuyet || "";
  
  document.getElementById("modalSo02Title").textContent = "Cập nhật Kế hoạch Triển khai";
  openModal("modalSo02");
};

window.deleteSo02Row = function(index) {
  if (confirm("Bạn có chắc chắn muốn xóa kế hoạch này không?")) {
    state.so02.splice(index, 1);
    saveStateToStorage(true);
  }
};

// 7.4. SỔ 03 - PHÁT SINH HĐ B-B'
function saveSo03Form(e) {
  e.preventDefault();
  const form = document.getElementById("formSo03");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("so03Index").value;
  const maBsc = document.getElementById("so03MaBsc").value;
  
  const data = {
    maPs: document.getElementById("so03MaPs").value,
    maBsc: maBsc,
    hangMuc: getHangMucByMaBsc(maBsc),
    ngayPs: document.getElementById("so03NgayPs").value,
    loai: document.getElementById("so03Loai").value,
    giaTri: parseFloat(document.getElementById("so03GiaTri").value) || 0,
    anhHuongTd: parseInt(document.getElementById("so03AnhHuongTd").value) || 0,
    moTa: document.getElementById("so03MoTa").value.trim(),
    nguyenNhan: document.getElementById("so03NguyenNhan").value.trim(),
    deXuat: document.getElementById("so03DeXuat").value.trim(),
    ttDuyet: document.getElementById("so03TtDuyet").value,
    nguoiDuyet: document.getElementById("so03NguoiDuyet").value.trim(),
    ngayDuyet: document.getElementById("so03NgayDuyet").value,
    linkHoSo: document.getElementById("so03LinkHoSo").value.trim(),
    noiDungDieuChinh: document.getElementById("so03NoidungDieuChinh").value.trim()
  };
  
  if (idxVal === "") {
    state.so03.push(data);
  } else {
    const index = parseInt(idxVal);
    state.so03[index] = data;
  }
  
  closeModal("modalSo03");
  saveStateToStorage(true);
}

window.editSo03Row = function(index) {
  const r = state.so03[index];
  if (!r) return;
  
  populateBscDropdown("so03MaBsc", r.maBsc);
  
  document.getElementById("so03Index").value = index;
  document.getElementById("so03MaPs").value = r.maPs;
  document.getElementById("so03HangMuc").value = r.hangMuc;
  document.getElementById("so03NgayPs").value = r.ngayPs;
  document.getElementById("so03Loai").value = r.loai;
  document.getElementById("so03GiaTri").value = r.giaTri;
  document.getElementById("so03AnhHuongTd").value = r.anhHuongTd;
  document.getElementById("so03MoTa").value = r.moTa;
  document.getElementById("so03NguyenNhan").value = r.nguyenNhan;
  document.getElementById("so03DeXuat").value = r.deXuat;
  document.getElementById("so03TtDuyet").value = r.ttDuyet;
  document.getElementById("so03NguoiDuyet").value = r.nguoiDuyet || "";
  document.getElementById("so03NgayDuyet").value = r.ngayDuyet || "";
  document.getElementById("so03LinkHoSo").value = r.linkHoSo;
  document.getElementById("so03NoidungDieuChinh").value = r.noiDungDieuChinh || "";
  
  document.getElementById("modalSo03Title").textContent = "Cập nhật Phát sinh " + r.maPs;
  openModal("modalSo03");
};

window.deleteSo03Row = function(index) {
  if (confirm("Bạn có chắc chắn muốn xóa phát sinh này không?")) {
    state.so03.splice(index, 1);
    saveStateToStorage(true);
  }
};

// 7.5. SỔ 04 - CUNG ỨNG ĐẶC THÙ
function saveSo04Form(e) {
  e.preventDefault();
  const form = document.getElementById("formSo04");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("so04Index").value;
  const maBsc = document.getElementById("so04MaBsc").value;
  
  const data = {
    maYc: document.getElementById("so04MaYc").value,
    maBsc: maBsc,
    hangMuc: getHangMucByMaBsc(maBsc),
    ngayYc: document.getElementById("so04NgayYc").value,
    loaiYc: document.getElementById("so04LoaiYc").value,
    vatTu: document.getElementById("so04VatTu").value.trim(),
    dacTa: document.getElementById("so04DacTa").value.trim(),
    kl: parseFloat(document.getElementById("so04Kl").value) || 0,
    dvt: document.getElementById("so04Dvt").value.trim(),
    giaTri: parseFloat(document.getElementById("so04GiaTri").value) || 0,
    trongNgoaiHd: document.getElementById("so04TrongNgoai").value,
    ngayCan: document.getElementById("so04NgayCan").value,
    ttDuyet: document.getElementById("so04TtDuyet").value,
    ttCungUng: document.getElementById("so04TtCungUng").value,
    linkHoSo: document.getElementById("so04LinkHoSo").value.trim()
  };
  
  if (idxVal === "") {
    state.so04.push(data);
  } else {
    const index = parseInt(idxVal);
    state.so04[index] = data;
  }
  
  closeModal("modalSo04");
  saveStateToStorage(true);
}

window.editSo04Row = function(index) {
  const r = state.so04[index];
  if (!r) return;
  
  populateBscDropdown("so04MaBsc", r.maBsc);
  
  document.getElementById("so04Index").value = index;
  document.getElementById("so04MaYc").value = r.maYc;
  document.getElementById("so04HangMuc").value = r.hangMuc;
  document.getElementById("so04NgayYc").value = r.ngayYc;
  document.getElementById("so04LoaiYc").value = r.loaiYc;
  document.getElementById("so04VatTu").value = r.vatTu;
  document.getElementById("so04DacTa").value = r.dacTa;
  document.getElementById("so04Kl").value = r.kl;
  document.getElementById("so04Dvt").value = r.dvt;
  document.getElementById("so04GiaTri").value = r.giaTri;
  document.getElementById("so04TrongNgoai").value = r.trongNgoaiHd;
  document.getElementById("so04NgayCan").value = r.ngayCan;
  document.getElementById("so04TtDuyet").value = r.ttDuyet;
  document.getElementById("so04TtCungUng").value = r.ttCungUng;
  document.getElementById("so04LinkHoSo").value = r.linkHoSo;
  
  document.getElementById("modalSo04Title").textContent = "Cập nhật Yêu cầu Cung ứng " + r.maYc;
  openModal("modalSo04");
};

window.deleteSo04Row = function(index) {
  if (confirm("Bạn có chắc chắn muốn xóa yêu cầu cung ứng này không?")) {
    state.so04.splice(index, 1);
    saveStateToStorage(true);
  }
};

// 7.6. SỔ 05 - BÙ TIẾN ĐỘ THI CÔNG
function saveSo05Form(e) {
  e.preventDefault();
  const form = document.getElementById("formSo05");
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }
  
  const idxVal = document.getElementById("so05Index").value;
  const maBsc = document.getElementById("so05MaBsc").value;
  
  const data = {
    maBsc: maBsc,
    hangMuc: getHangMucByMaBsc(maBsc),
    ngayPhatHien: document.getElementById("so05NgayPhatHien").value,
    mucCham: parseInt(document.getElementById("so05MucCham").value) || 0,
    nguyenNhan: document.getElementById("so05NguyenNhan").value.trim(),
    giaiPhapBu: document.getElementById("so05GiaiPhapBu").value.trim(),
    chiTietGiaiPhap: document.getElementById("so05ChiTietGiaiPhap").value.trim(),
    mocCamKet: document.getElementById("so05MocCamKet").value,
    linkPhuongAn: document.getElementById("so05LinkPhuongAn").value.trim(),
    ttDuyet: document.getElementById("so05TtDuyet").value,
    kqThucHienBu: document.getElementById("so05KqThucHienBu").value.trim(),
    ttThucHien: document.getElementById("so05TtThucHien").value
  };
  
  if (idxVal === "") {
    state.so05.push(data);
  } else {
    const index = parseInt(idxVal);
    state.so05[index] = data;
  }
  
  closeModal("modalSo05");
  saveStateToStorage(true);
}

window.editSo05Row = function(index) {
  const r = state.so05[index];
  if (!r) return;
  
  populateBscDropdown("so05MaBsc", r.maBsc);
  
  document.getElementById("so05Index").value = index;
  document.getElementById("so05HangMuc").value = r.hangMuc;
  document.getElementById("so05NgayPhatHien").value = r.ngayPhatHien;
  document.getElementById("so05MucCham").value = r.mucCham;
  document.getElementById("so05NguyenNhan").value = r.nguyenNhan;
  document.getElementById("so05GiaiPhapBu").value = r.giaiPhapBu;
  document.getElementById("so05ChiTietGiaiPhap").value = r.chiTietGiaiPhap;
  document.getElementById("so05MocCamKet").value = r.mocCamKet;
  document.getElementById("so05LinkPhuongAn").value = r.linkPhuongAn;
  document.getElementById("so05TtDuyet").value = r.ttDuyet;
  document.getElementById("so05KqThucHienBu").value = r.kqThucHienBu || "";
  document.getElementById("so05TtThucHien").value = r.ttThucHien;
  
  document.getElementById("modalSo05Title").textContent = "Cập nhật Bù Tiến Độ";
  openModal("modalSo05");
};

window.deleteSo05Row = function(index) {
  if (confirm("Bạn có chắc chắn muốn xóa bản ghi bù tiến độ này không?")) {
    state.so05.splice(index, 1);
    saveStateToStorage(true);
  }
};

// 8. CÁC HÀM TIỆN ÍCH KHÁC (UTILITIES)

// Định dạng hiển thị ngày DD/MM/YYYY
function formatDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const parts = dateStr.split("-");
    if (parts.length !== 3) return dateStr;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  } catch (e) {
    return dateStr;
  }
}

// Export dữ liệu sang tệp JSON
function exportDataToJson() {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `tender_lifecycle_backup_${new Date().toISOString().slice(0,10)}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

// Import dữ liệu từ tệp JSON
function importDataFromJson(e) {
  const fileReader = new FileReader();
  const file = e.target.files[0];
  if (!file) return;
  
  fileReader.onload = function(event) {
    try {
      const imported = JSON.parse(event.target.result);
      // Validate cấu trúc tối thiểu
      if (imported && imported.master && imported.so01) {
        state = imported;
        recalculateAllFormulas();
        saveStateToStorage(true);
        alert("Đã khôi phục dữ liệu từ tệp tin lưu trữ thành công!");
        switchTab("dashboard");
      } else {
        alert("Tệp tin JSON không đúng định dạng cấu trúc hệ thống. Vui lòng kiểm tra lại.");
      }
    } catch (err) {
      alert("Lỗi phân tích tệp tin JSON: " + err.message);
    }
  };
  fileReader.readAsText(file);
}

// ==========================================
// 🤖 HẠNG MỤC TÍCH HỢP AI GEMINI 3.5 FLASH
// ==========================================

let geminiApiKey = "";
let geminiModel = "gemini-1.5-flash";
let aiChatHistory = []; // Lưu lịch sử chat

// Khởi tạo cài đặt AI
function initAiSettings() {
  geminiApiKey = localStorage.getItem("VND_GEMINI_API_KEY") || "";
  geminiModel = localStorage.getItem("VND_GEMINI_MODEL") || "gemini-1.5-flash";
  document.getElementById("geminiApiKeyInput").value = geminiApiKey;
  document.getElementById("geminiModelSelect").value = geminiModel;
  updateAiStatusUI();
}

// Lưu API Key và Model
function saveApiKey(e) {
  if (e) e.preventDefault();
  const inputKey = document.getElementById("geminiApiKeyInput").value.trim();
  const selectModel = document.getElementById("geminiModelSelect").value;
  
  localStorage.setItem("VND_GEMINI_API_KEY", inputKey);
  localStorage.setItem("VND_GEMINI_MODEL", selectModel);
  
  geminiApiKey = inputKey;
  geminiModel = selectModel;
  
  updateAiStatusUI();
  alert("Đã lưu cấu hình AI thành công!");
}

// Cập nhật giao diện trạng thái AI
function updateAiStatusUI() {
  const dot = document.getElementById("aiStatusDot");
  const txt = document.getElementById("aiStatusText");
  
  if (geminiApiKey) {
    dot.style.backgroundColor = "var(--success)";
    txt.textContent = "AI Copilot Sẵn sàng";
    txt.style.color = "var(--success)";
  } else {
    dot.style.backgroundColor = "var(--danger)";
    txt.textContent = "AI Chưa cấu hình API Key";
    txt.style.color = "var(--text-muted)";
  }
}

// Gọi API Gemini REST với cơ chế tự phục hồi (Self-Healing Client)
async function callGeminiApi(promptText, options = {}) {
  if (!geminiApiKey) {
    alert("Vui lòng cấu hình Google Gemini API Key trong thanh Sidebar trước khi sử dụng tính năng này!");
    switchTab("dashboard");
    document.getElementById("geminiApiKeyInput").focus();
    throw new Error("API Key missing");
  }

  const requestBody = {
    contents: [
      {
        parts: [
          {
            text: promptText
          }
        ]
      }
    ]
  };

  // Cấu hình generationConfig tối ưu tốc độ phản hồi
  const config = {
    temperature: options.temperature !== undefined ? options.temperature : 0.2
  };
  if (options.isJsonMode) {
    config.responseMimeType = "application/json";
  }
  requestBody.generationConfig = config;

  // Các phương án URL kết nối xếp theo độ ưu tiên (Self-Healing Paths)
  const endpoints = [
    `https://generativelanguage.googleapis.com/v1/models/${geminiModel}:generateContent?key=${geminiApiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/${geminiModel}:generateContent?key=${geminiApiKey}`,
    `https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`,
    `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${geminiApiKey}`
  ];

  let lastError = null;

  for (let i = 0; i < endpoints.length; i++) {
    const url = endpoints[i];
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(requestBody)
      });

      if (response.ok) {
        const resData = await response.json();
        if (resData.candidates && resData.candidates[0]?.content?.parts[0]?.text) {
          console.log(`Kết nối AI thành công tại cổng kết nối thứ ${i + 1}`);
          return resData.candidates[0].content.parts[0].text;
        }
      }

      const errJson = await response.json().catch(() => ({}));
      lastError = new Error(errJson.error?.message || `HTTP error! status: ${response.status}`);
      console.warn(`Cổng kết nối thứ ${i + 1} gặp lỗi: ${lastError.message}`);
    } catch (err) {
      lastError = err;
      console.warn(`Lỗi kết nối mạng tại cổng thứ ${i + 1}: ${err.message}`);
    }
  }

  throw lastError || new Error("Không thể kết nối đến dịch vụ AI Gemini qua bất kỳ API version nào.");
}

// Copy báo cáo AI vào Clipboard
function copyAiReport() {
  const bodyText = document.getElementById("modalAiAnalysisBody").innerText;
  navigator.clipboard.writeText(bodyText)
    .then(() => alert("Đã sao chép báo cáo vào bộ nhớ tạm!"))
    .catch(err => alert("Lỗi sao chép: " + err));
}

// 🤖 AI FEATURE 1: PHÂN TÍCH CHI TIẾT TỪNG GÓI THẦU (MASTER ROW)
window.analyzeRowWithAi = async function(maBsc) {
  // Tìm dữ liệu master
  const row = state.master.find(m => m.maBsc === maBsc);
  if (!row) return;

  // Thu thập dữ liệu sổ phụ liên quan
  const so01_docs = state.so01.filter(item => item.maBsc === maBsc);
  const so02_plans = state.so02.filter(item => item.maBsc === maBsc);
  const so03_extras = state.so03.filter(item => item.maBsc === maBsc);
  const so04_supplies = state.so04.filter(item => item.maBsc === maBsc);
  const so05_delays = state.so05.filter(item => item.maBsc === maBsc);

  // Hiển thị modal loading
  document.getElementById("modalAiAnalysisTitle").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-primary"></i> Phân tích AI Gói thầu: ${maBsc}`;
  document.getElementById("modalAiAnalysisBody").innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 0; gap: 16px;">
      <div class="table-empty-icon" style="font-size: 3rem; animation: pulse 1.5s infinite;"><i class="fa-solid fa-wand-magic-sparkles text-primary"></i></div>
      <div style="font-weight: 600;" id="aiLoadingText">AI Gemini 3.5 đang phân tích gói thầu ${maBsc}...</div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">Đang tổng hợp thông tin, ngân sách, phát sinh và biện pháp bù tiến độ...</div>
    </div>
  `;
  openModal("modalAiAnalysis");

  // Xây dựng ngữ cảnh Prompt
  const docSummary = so01_docs.map(d => `- [${d.loaiHoSo}] ${d.tenSpham} (${d.ttDuyet})`).join("\n") || "Không có hồ sơ";
  const planSummary = so02_plans.map(p => `- KH ${p.thang}: ${p.noiDungChinh} (${p.ttDuyet})`).join("\n") || "Không có dữ liệu kế hoạch";
  const extraSummary = so03_extras.map(e => `- Phát sinh ${e.maPs}: ${e.loai} trị giá ${e.giaTri} tỷ, Chậm tiến độ: ${e.anhHuongTd} ngày (${e.ttDuyet})`).join("\n") || "Không có phát sinh chi phí";
  const supplySummary = so04_supplies.map(s => `- YC Cung ứng [${s.maYc}]: ${s.vatTu} (KL: ${s.kl} ${s.dvt}, trị giá ${s.giaTri} tỷ) - ${s.ttCungUng} (${s.ttDuyet})`).join("\n") || "Không có yêu cầu cung ứng đặc thù";
  const delaySummary = so05_delays.map(d => `- Phát hiện chậm: ${d.mucCham} ngày. Nguyên nhân: ${d.nguyenNhan}. Giải pháp bù: ${d.giaiPhapBu} (${d.ttThucHien})`).join("\n") || "Gói thầu hiện chưa ghi nhận sự cố chậm tiến độ đặc biệt";

  const promptText = `
Bạn là một Chuyên gia ERP thông minh, một Chuyên gia Phân tích Dữ liệu cao cấp kiêm Giám đốc Quản trị Rủi ro (Chief Risk Officer - CRO) dày dạn kinh nghiệm. Nhiệm vụ của bạn là đọc kỹ toàn bộ dữ liệu vận hành từ hệ thống được cung cấp đối với gói thầu thi công cụ thể dưới đây, tiến hành tổng hợp toàn diện, phân tích sâu dưới góc nhìn kiến trúc dữ liệu tích hợp nhằm đưa ra các cảnh báo rủi ro hệ thống quan trọng và lập phương án đề xuất xử lý mang tính chiến lược.

[THÔNG TIN GÓI THẦU CHI TIẾT]
- Mã BSC: ${row.maBsc}
- Hạng mục: ${row.hangMuc}
- Phân loại: ${row.goiThauPl} - Nhóm: ${row.nhomCt}
- Người phụ trách: ${row.phuTrach}
- Ngân sách dự toán: ${row.nganSach} tỷ VNĐ
- Giá trị hợp đồng ký kết: ${row.giaTriHdcu} tỷ VNĐ
- Điều kiện khởi công: ${row.dieuKienDu} (ĐK1: ${row.dk1}, ĐK2: ${row.dk2}, ĐK3: ${row.dk3})
- Ngày khởi công: ${row.ngayBdKhoiCong || 'Chưa khởi công'}
- Tiến độ tuần tháng này: T1 [${row.t1Dg || 'N/A'}], T2 [${row.t2Dg || 'N/A'}], T3 [${row.t3Dg || 'N/A'}], T4 [${row.t4Dg || 'N/A'}]
- Lũy kế Tổng Chi phí (Đã ký + Phát sinh đã duyệt): ${row.luyKeTongChiPhi} tỷ VNĐ
- Trạng thái bù tiến độ: ${row.buTienDo}

[DỮ LIỆU SỔ PHỤ CHI TIẾT ĐÍNH KÈM]
1. Hồ sơ tiền khởi công (Sổ 01):
${docSummary}
2. Kế hoạch triển khai (Sổ 02):
${planSummary}
3. Phát sinh hợp đồng B-B' (Sổ 03):
${extraSummary}
4. Yêu cầu cung ứng đặc thù (Sổ 04):
${supplySummary}
5. Nhật ký bù tiến độ thi công (Sổ 05):
${delaySummary}

HƯỚNG DẪN THỰC HIỆN (Chuỗi suy luận từng bước):
Hãy giải thích ngắn gọn tư duy lý luận chuyên gia của bạn ở đầu mỗi bước và trình bày báo cáo bằng tiếng Việt định dạng Markdown theo 3 bước sau:

Bước 1: Tổng hợp và Trích xuất thông tin cốt lõi (Data Synthesis)
Quét toàn bộ tập dữ liệu đầu vào để phân loại và làm rõ các ý chính, các xu hướng lớn hoặc các hạng mục chi phí/vận hành trọng yếu của gói thầu này.
Yêu cầu: Lập bảng tổng hợp các yếu tố cốt lõi (thông tin trích xuất, số liệu kèm theo nếu có, và tầm quan trọng của yếu tố đó).

Bước 2: Phân tích chuyên sâu & Đưa ra cảnh báo (Risk & Alert Analysis)
Dựa trên dữ liệu đã tổng hợp, thực hiện tư duy phản biện hệ thống ERP để tìm ra các "điểm thắt nút cổ chai", các sai lệch dữ liệu, hao hụt hoặc nguy cơ tiềm ẩn về mặt quản trị nguồn lực và tiến độ của gói thầu này.
Yêu cầu: Trình bày dưới dạng Bảng Cảnh báo trực quan gồm các cột: Vấn đề phát hiện | Mức độ nghiêm trọng (Thấp/Trung bình/Cao) | Nguyên nhân logic hệ thống | Hệ quả tiềm ẩn nếu không xử lý.

Bước 3: Đề xuất Phương án Xử lý & Khuyến nghị (Actionable Solutions)
Đối với mỗi rủi ro hoặc điểm nghẽn dữ liệu đã chỉ ra ở Bước 2, hãy đưa ra khuyến nghị chiến lược cụ thể và khả thi để khắc phục hoặc tối ưu hóa vận hành quy trình.
Yêu cầu: Trình bày dưới dạng danh sách gạch đầu dòng rõ ràng, phân định rõ giải pháp ngắn hạn (sửa sai ngay lập tức) và giải pháp dài hạn (phòng ngừa bền vững, chuẩn hóa quy trình).
  `;

  try {
    const responseText = await callGeminiApi(promptText);
    const md = window.markdownit({ html: true, linkify: true });
    document.getElementById("modalAiAnalysisBody").innerHTML = md.render(responseText);
  } catch (err) {
    if (err.message !== "API Key missing") {
      document.getElementById("modalAiAnalysisBody").innerHTML = `
        <div class="alert-item alert-error" style="margin-top: 20px;">
          <span class="alert-item-icon"><i class="fa-solid fa-circle-exclamation"></i></span>
          <div class="alert-item-content">
            <div class="alert-item-title">Lỗi kết nối AI Gemini</div>
            <div class="alert-item-desc">${err.message || 'Không thể kết nối với dịch vụ của Google. Vui lòng kiểm tra lại mạng Internet và tính hợp lệ của API Key.'}</div>
          </div>
        </div>
      `;
    } else {
      closeModal("modalAiAnalysis");
    }
  }
};

// 🤖 AI FEATURE 2: PHÂN TÍCH RỦI RO TOÀN CỤC DỰ ÁN (DASHBOARD)
window.analyzeProjectWithAi = async function() {
  // Gom dữ liệu tổng quan toàn bộ dự án
  const totalBudget = state.master.reduce((sum, r) => sum + (parseFloat(r.nganSach) || 0), 0);
  const totalContract = state.master.reduce((sum, r) => r.ttHdcu === "Đã ký" ? sum + (parseFloat(r.giaTriHdcu) || 0) : sum, 0);
  const totalExtra = state.so03.reduce((sum, r) => r.ttDuyet === "Đã duyệt" ? sum + (parseFloat(r.giaTri) || 0) : sum, 0);
  
  const masterSummary = state.master.map(r => 
    `- Gói thầu [${r.maBsc}] - ${r.hangMuc}: Ngân sách ${r.nganSach} tỷ, Giá trị HĐ ${r.giaTriHdcu} tỷ, Trạng thái bù tiến độ [${r.buTienDo}], ĐK Khởi công [${r.dieuKienDu}].`
  ).join("\n");
  
  const activeDelays = state.so05.filter(d => d.ttThucHien !== "Đã bắt kịp tiến độ");
  const delaySummary = activeDelays.map(d => 
    `- Gói thầu [${d.maBsc}] chậm ${d.mucCham} ngày. Lý do: ${d.nguyenNhan}. Trạng thái bù: ${d.ttThucHien}.`
  ).join("\n") || "Không có gói thầu nào ghi nhận chậm tiến độ hiện tại.";
  
  const pendingExtras = state.so03.filter(e => e.ttDuyet === "Chờ duyệt");
  const pendingExtraSummary = pendingExtras.map(e => 
    `- [${e.maPs}] Gói thầu ${e.maBsc}: ${e.moTa} (Ước tính ${e.giaTri} tỷ, Chậm tiến độ ${e.anhHuongTd} ngày)`
  ).join("\n") || "Không có hồ sơ phát sinh nào đang chờ duyệt.";

  // Hiển thị modal loading
  document.getElementById("modalAiAnalysisTitle").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-primary"></i> Báo cáo Đánh giá Rủi ro Toàn dự án`;
  document.getElementById("modalAiAnalysisBody").innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 0; gap: 16px;">
      <div class="table-empty-icon" style="font-size: 3rem; animation: pulse 1.5s infinite;"><i class="fa-solid fa-wand-magic-sparkles text-primary"></i></div>
      <div style="font-weight: 600;" id="aiLoadingText">AI Gemini 3.5 đang phân tích toàn bộ dự án...</div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">Đang đối chiếu dữ liệu thầu, lũy kế phát sinh và các sự cố tiến độ...</div>
    </div>
  `;
  openModal("modalAiAnalysis");

  const promptText = `
Bạn là một Chuyên gia ERP thông minh, một Chuyên gia Phân tích Dữ liệu cao cấp kiêm Giám đốc Quản trị Rủi ro (Chief Risk Officer - CRO) dày dạn kinh nghiệm. Nhiệm vụ của bạn là đọc kỹ toàn bộ dữ liệu tổng quan và dữ liệu vận hành từ hệ thống dự án được cung cấp dưới đây, tiến hành tổng hợp toàn diện, phân tích sâu dưới góc nhìn kiến trúc dữ liệu tích hợp nhằm đưa ra các cảnh báo rủi ro hệ thống quan trọng và lập phương án đề xuất xử lý mang tính chiến lược.

[THÔNG SỐ VẬN HÀNH ĐẦU NÃO DỰ ÁN]
- Tổng ngân sách định biên: ${totalBudget} tỷ VNĐ
- Tổng giá trị hợp đồng đã ký kết: ${totalContract} tỷ VNĐ
- Tổng chi phí phát sinh bổ sung đã phê duyệt: ${totalExtra} tỷ VNĐ
- Lũy kế Tổng đầu tư thực tế hiện tại: ${totalContract + totalExtra} tỷ VNĐ

[TÌNH TRẠNG CÁC GÓI THẦU MASTER]
${masterSummary}

[ĐIỂM NÓNG CHẬM TIẾN ĐỘ THỰC TẾ]
${delaySummary}

[HỒ SƠ PHÁT SINH CHỜ QUYẾT ĐỊNH]
${pendingExtraSummary}

HƯỚNG DẪN THỰC HIỆN (Chuỗi suy luận từng bước):
Hãy giải thích ngắn gọn tư duy lý luận chuyên gia của bạn ở đầu mỗi bước và trình bày báo cáo bằng tiếng Việt định dạng Markdown theo 3 bước sau:

Bước 1: Tổng hợp và Trích xuất thông tin cốt lõi (Data Synthesis)
Quét toàn bộ tập dữ liệu đầu vào để phân loại và làm rõ các ý chính, các xu hướng lớn hoặc các hạng mục chi phí/vận hành trọng yếu của toàn bộ dự án.
Yêu cầu: Lập bảng tổng hợp các yếu tố cốt lõi (thông tin trích xuất, số liệu kèm theo nếu có, và tầm quan trọng của yếu tố đó).

Bước 2: Phân tích chuyên sâu & Đưa ra cảnh báo (Risk & Alert Analysis)
Dựa trên dữ liệu đã tổng hợp, thực hiện tư duy phản biện hệ thống ERP để tìm ra các "điểm thắt nút cổ chai", các sai lệch dữ liệu, hao hụt hoặc nguy cơ tiềm ẩn về mặt quản trị nguồn lực toàn bộ dự án.
Yêu cầu: Trình bày dưới dạng Bảng Cảnh báo trực quan gồm các cột: Vấn đề phát hiện | Mức độ nghiêm trọng (Thấp/Trung bình/Cao) | Nguyên nhân logic hệ thống | Hệ quả tiềm ẩn nếu không xử lý.

Bước 3: Đề xuất Phương án Xử lý & Khuyến nghị (Actionable Solutions)
Đối với mỗi rủi ro hoặc điểm nghẽn dữ liệu đã chỉ ra ở Bước 2, hãy đưa ra khuyến nghị chiến lược cụ thể và khả thi để khắc phục hoặc tối ưu hóa vận hành quy trình.
Yêu cầu: Trình bày dưới dạng danh sách gạch đầu dòng rõ ràng, phân định rõ giải pháp ngắn hạn (sửa sai ngay lập tức) và giải pháp dài hạn (phòng ngừa bền vững, chuẩn hóa quy trình).
  `;

  try {
    const responseText = await callGeminiApi(promptText);
    const md = window.markdownit({ html: true, linkify: true });
    document.getElementById("modalAiAnalysisBody").innerHTML = md.render(responseText);
  } catch (err) {
    if (err.message !== "API Key missing") {
      document.getElementById("modalAiAnalysisBody").innerHTML = `
        <div class="alert-item alert-error" style="margin-top: 20px;">
          <span class="alert-item-icon"><i class="fa-solid fa-circle-exclamation"></i></span>
          <div class="alert-item-content">
            <div class="alert-item-title">Lỗi kết nối AI Gemini</div>
            <div class="alert-item-desc">${err.message || 'Không thể kết nối với AI.'}</div>
          </div>
        </div>
      `;
    } else {
      closeModal("modalAiAnalysis");
    }
  }
};

// 🤖 AI FEATURE 3: CHATBOT AI COPILOT ĐA NĂNG
function toggleChatWindow() {
  const windowEl = document.getElementById("chatWindow");
  windowEl.classList.toggle("active");
}

async function sendChatMessage() {
  const inputEl = document.getElementById("chatInput");
  const messageText = inputEl.value.trim();
  if (!messageText) return;
  
  // Hiển thị câu hỏi của User
  const chatMessages = document.getElementById("chatMessages");
  const userMsgDiv = document.createElement("div");
  userMsgDiv.className = "chat-msg user-msg";
  userMsgDiv.textContent = messageText;
  chatMessages.appendChild(userMsgDiv);
  
  // Clear input
  inputEl.value = "";
  chatMessages.scrollTop = chatMessages.scrollHeight;
  
  // Tạo loading bubble cho AI
  const aiLoadingDiv = document.createElement("div");
  aiLoadingDiv.className = "chat-msg ai-msg";
  aiLoadingDiv.innerHTML = `<i class="fa-solid fa-ellipsis" style="animation: pulse 1s infinite;"></i> Đang suy nghĩ...`;
  chatMessages.appendChild(aiLoadingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  // Gom gọn dữ liệu dự án hiện tại làm ngữ cảnh
  const projectSummary = state.master.map(r => {
    return {
      maBsc: r.maBsc,
      hangMuc: r.hangMuc,
      nganSach: r.nganSach,
      giaTriHd: r.giaTriHdcu,
      dkKhoiCong: r.dieuKienDu,
      buTienDo: r.buTienDo,
      phatSinhChuaDuyet: r.phatSinhChuaDuyet,
      cungUngChuaDuyet: r.cungUngChuaDuyet
    };
  });
  
  const pendingExtras = state.so03.filter(e => e.ttDuyet === "Chờ duyệt").map(e => ({
    maBsc: e.maBsc, maPs: e.maPs, giaTri: e.giaTri, moTa: e.moTa
  }));

  const activeDelays = state.so05.filter(d => d.ttThucHien !== "Đã bắt kịp tiến độ").map(d => ({
    maBsc: d.maBsc, mucCham: d.mucCham, nguyenNhan: d.nguyenNhan, giaiPhap: d.giaiPhapBu
  }));

  const promptContext = `
Bạn là Trợ lý AI Copilot chuyên nghiệp (AI Gemini 3.5 Flash) tích hợp trong "Hệ thống kiểm soát khép kín vòng đời gói thầu thi công".
Nhiệm vụ của bạn là hỗ trợ giải đáp các câu hỏi của người dùng về tình hình dự án một cách chính xác dựa trên cơ sở dữ liệu hiện tại được cung cấp dưới đây.

[DỮ LIỆU HỆ THỐNG DỰ ÁN]
- Danh sách gói thầu Master:
${JSON.stringify(projectSummary, null, 2)}

- Danh sách Phát sinh HĐ chờ duyệt:
${JSON.stringify(pendingExtras, null, 2)}

- Danh sách các sự cố chậm tiến độ đang chạy:
${JSON.stringify(activeDelays, null, 2)}

YÊU CẦU:
1. Trả lời trực tiếp, rõ ràng câu hỏi của người dùng bằng tiếng Việt.
2. Luôn đối chiếu và sử dụng chính xác các số liệu hoặc thông tin trong phần [DỮ LIỆU HỆ THỐNG DỰ ÁN].
3. Nếu người dùng hỏi các thông tin nằm ngoài phạm vi dữ liệu dự án trên, hãy khéo léo thông báo bạn không có dữ liệu để phân tích và hướng dẫn họ nhập thông tin vào các bảng nghiệp vụ.

[CÂU HỎI CỦA NGƯỜI DÙNG]: "${messageText}"
  `;

  try {
    const responseText = await callGeminiApi(promptContext);
    
    // Gỡ bỏ bubble loading
    aiLoadingDiv.remove();
    
    // Hiển thị câu trả lời AI
    const aiMsgDiv = document.createElement("div");
    aiMsgDiv.className = "chat-msg ai-msg";
    
    // Render markdown kết quả gọn nhẹ
    const md = window.markdownit({ html: true, linkify: true });
    aiMsgDiv.innerHTML = md.render(responseText);
    
    chatMessages.appendChild(aiMsgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  } catch (err) {
    aiLoadingDiv.remove();
    const errorDiv = document.createElement("div");
    errorDiv.className = "chat-msg ai-msg";
    errorDiv.style.color = "var(--danger)";
    errorDiv.style.borderColor = "rgba(220, 38, 38, 0.2)";
    errorDiv.innerHTML = `<i class="fa-solid fa-circle-exclamation"></i> <strong>Lỗi kết nối AI:</strong> ${err.message || 'Vui lòng kiểm tra lại API Key.'}`;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }
}

// ==========================================
// 📊 HẠNG MỤC IMPORT & EXPORT EXCEL (.XLSX)
// ==========================================

// Xuất toàn bộ cơ sở dữ liệu (6 Sheets) sang file Excel
function exportToExcel() {
  if (typeof XLSX === "undefined") {
    alert("Thư viện SheetJS chưa được tải thành công. Vui lòng kiểm tra lại kết nối mạng!");
    return;
  }

  // Khởi tạo workbook mới
  const wb = XLSX.utils.book_new();

  // Hàm ánh xạ thuộc tính tiếng Anh sang Tiêu đề tiếng Việt
  const mapData = (array, headersMap) => {
    return array.map(item => {
      const newItem = {};
      for (const [engKey, viHeader] of Object.entries(headersMap)) {
        newItem[viHeader] = item[engKey] !== undefined ? item[engKey] : "";
      }
      return newItem;
    });
  };

  // 1. MASTER_DATA mapping
  const masterMap = {
    tt: "TT", maBsc: "Mã BSC", goiThauPl: "Gói thầu (PL)", nhomCt: "Nhóm CT",
    hangMuc: "Hạng mục / Công việc", phuTrach: "Phụ trách", ngayBdYc: "Ngày BĐ (YC CĐT)",
    ngayKtYc: "Ngày KT (YC CĐT)", nganSach: "Ngân sách (tỷ)", khHstktc: "KH phát hành HSTKTC",
    ttHstktc: "TT HSTKTC", ttSpecs: "TT SPECS", ttBoq: "TT BOQ/KL", khLcnt: "KH LCNT",
    ttLcnt: "TT LCNT", khHdcu: "KH Ký HĐCU", ttHdcu: "TT Ký HĐCU", khPdKhcu: "KH PD KHCU",
    ttKhcu: "TT KHCU", giaTriHdcu: "Giá trị HĐCU (tỷ)", tileHdcuNs: "% HĐCU/NS",
    khPlhdCdt: "KH ký PLHĐ CĐT", ttPlhdCdt: "TT Ký PLHĐ CĐT", khPdKhtk: "KH PD KHTK",
    ttKhtk: "TT KHTK", dk1: "ĐK1 HSKT đủ", dk2: "ĐK2 HĐCU ký", dk3: "ĐK3 KHTK duyệt",
    dieuKienDu: "ĐIỀU KIỆN ĐỦ", ngayBdKhoiCong: "NGÀY BĐ KHỞI CÔNG", hsTienKc: "HS tiền KC (duyệt)",
    luyKeGiaTriHdAB: "LŨY KẾ GIÁ TRỊ HĐ A - B", luyKePhatSinhBB: "LŨY KẾ PHÁT SINH HĐ B - B'",
    luyKeTongChiPhi: "LŨY KẾ TỔNG CHI PHÍ/ NGÂN SÁCH", taiLieuKhThang: "Tài liệu KH tháng (duyệt/tổng)",
    phatSinhChuaDuyet: "Phát sinh chưa duyệt", cungUngChuaDuyet: "YC cung ứng chờ duyệt",
    buTienDo: "Bù tiến độ đang chạy", khQaQc: "KH KLCV tháng - QA/QC", kqQaQc: "KQ KLCV tháng - QA/QC",
    dgQaQc: "Đánh giá & giải pháp tháng - QA/QC", khThiCong: "KH KLCV tháng - Thi công",
    kqThiCong: "KQ KLCV tháng - Thi công", dgThiCong: "Đánh giá & giải pháp tháng - Thi công",
    t1Kh: "T1 KH", t1Kq: "T1 KQ", t1Dg: "T1 Đánh giá",
    t2Kh: "T2 KH", t2Kq: "T2 KQ", t2Dg: "T2 Đánh giá",
    t3Kh: "T3 KH", t3Kq: "T3 KQ", t3Dg: "T3 Đánh giá",
    t4Kh: "T4 KH", t4Kq: "T4 KQ", t4Dg: "T4 Đánh giá"
  };
  const masterData = mapData(state.master, masterMap);
  const wsMaster = XLSX.utils.json_to_sheet(masterData);
  XLSX.utils.book_append_sheet(wb, wsMaster, "MASTER_DATA");

  // 2. SO_01 mapping
  const so01Map = {
    stt: "STT", maBsc: "Mã BSC", hangMuc: "Hạng mục", loaiHoSo: "Loại hồ sơ",
    tenSpham: "Tên sản phẩm / Số hiệu", linkLuuTru: "LINK lưu trữ", ngayHt: "Ngày HT",
    nguoiLap: "Người lập", nguoiDuyet: "Người duyệt", ttDuyet: "TT duyệt"
  };
  const so01Data = mapData(state.so01, so01Map);
  const wsSo01 = XLSX.utils.json_to_sheet(so01Data);
  XLSX.utils.book_append_sheet(wb, wsSo01, "SO_01_TIEN_KHOI_CONG");

  // 3. SO_02 mapping
  const so02Map = {
    stt: "STT", maBsc: "Mã BSC", hangMuc: "Hạng mục", thang: "Tháng",
    loaiTaiLieu: "Loại tài liệu", noiDungChinh: "Nội dung chính", datYckt: "Đạt YCKT CĐT",
    linkTaiLieu: "LINK tài liệu", ttLap: "TT lập", ttDuyet: "TT duyệt",
    nguoiLap: "Người lập", nguoiDuyet: "Người duyệt", ngayDuyet: "Ngày duyệt"
  };
  const so02Data = mapData(state.so02, so02Map);
  const wsSo02 = XLSX.utils.json_to_sheet(so02Data);
  XLSX.utils.book_append_sheet(wb, wsSo02, "SO_02_KE_HOACH");

  // 4. SO_03 mapping
  const so03Map = {
    maPs: "Mã PS", maBsc: "Mã BSC", hangMuc: "Hạng mục", ngayPs: "Ngày PS",
    loai: "Loại", moTa: "Mô tả", nguyenNhan: "Nguyên nhân", deXuat: "Đề xuất xử lý",
    giaTri: "Giá trị (tỷ)", anhHuongTd: "Ảnh hưởng TĐ (ngày)", linkHoSo: "LINK hồ sơ",
    ttDuyet: "TT duyệt", nguoiDuyet: "Người duyệt", ngayDuyet: "Ngày duyệt",
    noiDungDieuChinh: "Nội dung điều chỉnh (KH→KQ)"
  };
  const so03Data = mapData(state.so03, so03Map);
  const wsSo03 = XLSX.utils.json_to_sheet(so03Data);
  XLSX.utils.book_append_sheet(wb, wsSo03, "SO_03_PHAT_SINH");

  // 5. SO_04 mapping
  const so04Map = {
    maYc: "Mã YC", maBsc: "Mã BSC", hangMuc: "Hạng mục", ngayYc: "Ngày YC",
    loaiYc: "Loại YC", vatTu: "Vật tư / Thiết bị", dacTa: "Đặc tả KT / Lý do",
    kl: "KL", dvt: "ĐVT", giaTri: "Giá trị (tỷ)", trongNgoaiHd: "Trong/Ngoài HĐCU",
    linkHoSo: "LINK hồ sơ", ttDuyet: "TT duyệt", ngayCan: "Ngày cần", ttCungUng: "TT cung ứng"
  };
  const so04Data = mapData(state.so04, so04Map);
  const wsSo04 = XLSX.utils.json_to_sheet(so04Data);
  XLSX.utils.book_append_sheet(wb, wsSo04, "SO_04_CUNG_UNG");

  // 6. SO_05 mapping
  const so05Map = {
    stt: "STT", maBsc: "Mã BSC", hangMuc: "Hạng mục", ngayPhatHien: "Ngày phát hiện",
    mucCham: "Mức chậm (ngày)", nguyenNhan: "Nguyên nhân", giaiPhapBu: "Giải pháp bù",
    chiTietGiaiPhap: "Chi tiết giải pháp", mocCamKet: "Mốc cam kết HT", linkPhuongAn: "LINK phương án",
    ttDuyet: "TT duyệt", kqThucHienBu: "KQ thực hiện bù", ttThucHien: "TT thực hiện"
  };
  const so05Data = mapData(state.so05, so05Map);
  const wsSo05 = XLSX.utils.json_to_sheet(so05Data);
  XLSX.utils.book_append_sheet(wb, wsSo05, "SO_05_BU_TIEN_DO");

  // Tải file Excel Workbook
  XLSX.writeFile(wb, `Ke_hoach_VSV_Tender_Data_${new Date().toISOString().slice(0,10)}.xlsx`);
}

// Nhập toàn bộ cơ sở dữ liệu từ file Excel
// Nhập toàn bộ cơ sở dữ liệu từ file Excel
function importFromExcel(e) {
  if (typeof XLSX === "undefined") {
    alert("Thư viện SheetJS chưa được tải thành công. Vui lòng kiểm tra lại kết nối mạng!");
    return;
  }

  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = function(event) {
    try {
      const data = new Uint8Array(event.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      
      const newState = { master: [], so01: [], so02: [], so03: [], so04: [], so05: [] };

      // Helper function to clean string
      const cleanStr = (val) => {
        if (val === undefined || val === null) return "";
        return String(val).trim();
      };

      // Helper function to parse float
      const cleanFloat = (val) => {
        if (val === undefined || val === null || val === "") return 0;
        const num = parseFloat(String(val).replace(/,/g, ''));
        return isNaN(num) ? 0 : num;
      };

      // Helper function to parse int
      const cleanInt = (val) => {
        if (val === undefined || val === null || val === "") return 0;
        const num = parseInt(String(val).replace(/,/g, ''));
        return isNaN(num) ? 0 : num;
      };

      // Helper function to format Excel date to YYYY-MM-DD
      const cleanDate = (val) => {
        if (val === undefined || val === null || val === "") return "";
        if (typeof val === "number") {
          const date = new Date((val - 25569) * 86400 * 1000);
          const y = date.getFullYear();
          const m = String(date.getMonth() + 1).padStart(2, '0');
          const d = String(date.getDate()).padStart(2, '0');
          return `${y}-${m}-${d}`;
        }
        const str = String(val).trim();
        if (str.match(/^\d{4}-\d{2}-\d{2}$/)) return str;
        const parsed = Date.parse(str);
        if (!isNaN(parsed)) {
          const date = new Date(parsed);
          const y = date.getFullYear();
          const m = String(date.getMonth() + 1).padStart(2, '0');
          const d = String(date.getDate()).padStart(2, '0');
          return `${y}-${m}-${d}`;
        }
        return str;
      };

      // 1. Đọc sheet MASTER_DATA hoặc BANG TONG HOP
      let wsMaster = workbook.Sheets["BANG TONG HOP"] || workbook.Sheets["MASTER_DATA"];
      if (wsMaster) {
        const rows = XLSX.utils.sheet_to_json(wsMaster, { header: 1 });
        let currentPl = null;
        let startIndex = 5;
        if (rows[0] && String(rows[0][0]).toUpperCase() === "TT") {
          startIndex = 1;
        } else if (rows[3] && String(rows[3][0]).toUpperCase() === "TT") {
          startIndex = 4;
        } else if (rows[4] && String(rows[4][0]).toUpperCase() === "TT") {
          startIndex = 5;
        }
        
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 5) continue;
          if (!row[0] && !row[4]) continue;
          
          let tt = cleanStr(row[0]);
          let maBsc = cleanStr(row[1]);
          let goiThauPl = cleanStr(row[2]);
          
          if (goiThauPl && goiThauPl.toUpperCase().startsWith("PL")) {
            currentPl = goiThauPl;
          }
          if (!goiThauPl || !goiThauPl.toUpperCase().startsWith("PL")) {
            if (currentPl) {
              goiThauPl = currentPl;
            } else {
              continue;
            }
          }
          
          newState.master.push({
            tt: tt,
            maBsc: maBsc,
            goiThauPl: goiThauPl,
            nhomCt: cleanStr(row[3]),
            hangMuc: cleanStr(row[4]),
            phuTrach: cleanStr(row[5]),
            ngayBdYc: cleanDate(row[6]),
            ngayKtYc: cleanDate(row[7]),
            nganSach: cleanFloat(row[8]),
            khHstktc: cleanDate(row[9]),
            ttHstktc: cleanStr(row[10]),
            ttSpecs: cleanStr(row[11]),
            ttBoq: cleanStr(row[12]),
            khLcnt: cleanDate(row[13]),
            ttLcnt: cleanStr(row[14]),
            khHdcu: cleanDate(row[15]),
            ttHdcu: cleanStr(row[16]),
            khPdKhcu: cleanDate(row[17]),
            ttKhcu: cleanStr(row[18]),
            giaTriHdcu: cleanFloat(row[19]),
            khPlhdCdt: cleanDate(row[21]),
            ttPlhdCdt: cleanStr(row[22]),
            khPdKhtk: cleanDate(row[23]),
            ttKhtk: cleanStr(row[24]),
            ngayBdKhoiCong: cleanDate(row[29]),
            luyKeGiaTriHdAB: cleanFloat(row[33]),
            buTienDo: cleanStr(row[34]),
            khQaQc: cleanStr(row[38]),
            kqQaQc: cleanStr(row[39]),
            dgQaQc: cleanStr(row[40]),
            khThiCong: cleanStr(row[41]),
            kqThiCong: cleanStr(row[42]),
            dgThiCong: cleanStr(row[43]),
            t1Kh: cleanStr(row[44]),
            t1Kq: cleanStr(row[45]),
            t1Dg: cleanStr(row[46]),
            t2Kh: cleanStr(row[47]),
            t2Kq: cleanStr(row[48]),
            t2Dg: cleanStr(row[49]),
            t3Kh: cleanStr(row[50]),
            t3Kq: cleanStr(row[51]),
            t3Dg: cleanStr(row[52]),
            t4Kh: cleanStr(row[53]),
            t4Kq: cleanStr(row[54]),
            t4Dg: cleanStr(row[55])
          });
        }
      }

      // 2. Đọc sheet SO_01_TIEN_KHOI_CONG hoặc 01_HSo TienKC
      let wsSo01 = workbook.Sheets["01_HSo TienKC"] || workbook.Sheets["SO_01_TIEN_KHOI_CONG"];
      if (wsSo01) {
        const rows = XLSX.utils.sheet_to_json(wsSo01, { header: 1 });
        let startIndex = 1;
        if (rows[1] && (String(rows[1][0]).toUpperCase() === "STT" || String(rows[1][1]).toUpperCase() === "M\u00C3 BSC")) {
          startIndex = 2;
        }
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 4 || !row[1]) continue;
          newState.so01.push({
            stt: cleanInt(row[0]),
            maBsc: cleanStr(row[1]),
            hangMuc: cleanStr(row[2]),
            loaiHoSo: cleanStr(row[3]),
            tenSpham: cleanStr(row[4]),
            linkLuuTru: cleanStr(row[5]),
            ngayHt: cleanDate(row[6]),
            nguoiLap: cleanStr(row[7]),
            nguoiDuyet: cleanStr(row[8]),
            ttDuyet: cleanStr(row[9])
          });
        }
      }

      // 3. Đọc sheet SO_02_KE_HOACH hoặc 02_KH Thang_Tuan
      let wsSo02 = workbook.Sheets["02_KH Thang_Tuan"] || workbook.Sheets["SO_02_KE_HOACH"];
      if (wsSo02) {
        const rows = XLSX.utils.sheet_to_json(wsSo02, { header: 1 });
        let startIndex = 1;
        if (rows[1] && (String(rows[1][0]).toUpperCase() === "STT" || String(rows[1][1]).toUpperCase() === "M\u00C3 BSC")) {
          startIndex = 2;
        }
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 5 || !row[1]) continue;
          newState.so02.push({
            stt: cleanInt(row[0]),
            maBsc: cleanStr(row[1]),
            hangMuc: cleanStr(row[2]),
            thang: cleanStr(row[3]),
            loaiTaiLieu: cleanStr(row[4]),
            noiDungChinh: cleanStr(row[5]),
            datYckt: cleanStr(row[6]),
            linkTaiLieu: cleanStr(row[7]),
            ttLap: cleanStr(row[8]),
            ttDuyet: cleanStr(row[9]),
            nguoiLap: cleanStr(row[10]),
            nguoiDuyet: cleanStr(row[11]),
            ngayDuyet: cleanDate(row[12])
          });
        }
      }

      // 4. Đọc sheet SO_03_PHAT_SINH hoặc 03_Phat sinh
      let wsSo03 = workbook.Sheets["03_Phat sinh"] || workbook.Sheets["SO_03_PHAT_SINH"];
      if (wsSo03) {
        const rows = XLSX.utils.sheet_to_json(wsSo03, { header: 1 });
        let startIndex = 1;
        if (rows[1] && (String(rows[1][0]).toUpperCase() === "M\u00C3 PS" || String(rows[1][2]).toUpperCase() === "M\u00C3 BSC")) {
          startIndex = 2;
        }
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 5 || !row[2]) continue;
          newState.so03.push({
            maPs: cleanStr(row[0]),
            stt: cleanInt(row[1]),
            maBsc: cleanStr(row[2]),
            hangMuc: cleanStr(row[3]),
            ngayPs: cleanDate(row[4]),
            loai: cleanStr(row[5]),
            moTa: cleanStr(row[6]),
            nguyenNhan: cleanStr(row[7]),
            deXuat: cleanStr(row[8]),
            giaTri: cleanFloat(row[9]),
            anhHuongTd: cleanInt(row[10]),
            linkHoSo: cleanStr(row[11]),
            ttDuyet: cleanStr(row[12]),
            nguoiDuyet: cleanStr(row[13]),
            ngayDuyet: cleanDate(row[14]),
            noiDungDieuChinh: cleanStr(row[15])
          });
        }
      }

      // 5. Đọc sheet SO_04_CUNG_UNG hoặc 04_CU dac thu
      let wsSo04 = workbook.Sheets["04_CU dac thu"] || workbook.Sheets["SO_04_CUNG_UNG"];
      if (wsSo04) {
        const rows = XLSX.utils.sheet_to_json(wsSo04, { header: 1 });
        let startIndex = 1;
        if (rows[1] && (String(rows[1][0]).toUpperCase() === "M\u00C3 YC" || String(rows[1][2]).toUpperCase() === "M\u00C3 BSC")) {
          startIndex = 2;
        }
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 5 || !row[2]) continue;
          newState.so04.push({
            maYc: cleanStr(row[0]),
            stt: cleanInt(row[1]),
            maBsc: cleanStr(row[2]),
            hangMuc: cleanStr(row[3]),
            ngayYc: cleanDate(row[4]),
            loaiYc: cleanStr(row[5]),
            vatTu: cleanStr(row[6]),
            dacTa: cleanStr(row[7]),
            kl: cleanFloat(row[8]),
            dvt: cleanStr(row[9]),
            giaTri: cleanFloat(row[10]),
            trongNgoaiHd: cleanStr(row[11]),
            linkHoSo: cleanStr(row[12]),
            ttDuyet: cleanStr(row[13]),
            ngayCan: cleanDate(row[14]),
            ttCungUng: cleanStr(row[15])
          });
        }
      }

      // 6. Đọc sheet SO_05_BU_TIEN_DO hoặc 05_Bu tien do
      let wsSo05 = workbook.Sheets["05_Bu tien do"] || workbook.Sheets["SO_05_BU_TIEN_DO"];
      if (wsSo05) {
        const rows = XLSX.utils.sheet_to_json(wsSo05, { header: 1 });
        let startIndex = 1;
        if (rows[1] && (String(rows[1][0]).toUpperCase() === "STT" || String(rows[1][1]).toUpperCase() === "M\u00C3 BSC")) {
          startIndex = 2;
        }
        for (let i = startIndex; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length < 4 || !row[1]) continue;
          newState.so05.push({
            stt: cleanInt(row[0]),
            maBsc: cleanStr(row[1]),
            hangMuc: cleanStr(row[2]),
            ngayPhatHien: cleanDate(row[3]),
            mucCham: cleanInt(row[4]),
            nguyenNhan: cleanStr(row[5]),
            giaiPhapBu: cleanStr(row[6]),
            chiTietGiaiPhap: cleanStr(row[7]),
            mocCamKet: cleanDate(row[8]),
            linkPhuongAn: cleanStr(row[9]),
            ttDuyet: cleanStr(row[10]),
            kqThucHienBu: cleanStr(row[11]),
            ttThucHien: cleanStr(row[12])
          });
        }
      }

      // Đồng bộ và cập nhật lại giao diện
      if (newState.master.length > 0) {
        state = newState;
        recalculateAllFormulas();
        saveStateToStorage(true);
        alert("Đã nhập dữ liệu từ file Excel thành công! Hệ thống đã tự động tính toán lại toàn bộ công thức liên kết và phân cấp gói thầu.");
        switchTab("dashboard");
      } else {
        alert("Không tìm thấy dữ liệu BANG TONG HOP hoặc MASTER_DATA hợp lệ trong tệp Excel. Vui lòng kiểm tra lại tên sheet.");
      }
    } catch (err) {
      alert("Lỗi phân tích tệp Excel: " + err.message);
      console.error(err);
    }
  };
  reader.readAsArrayBuffer(file);
}

// ==========================================
// 🧠 HẠNG MỤC NHẬP DỮ LIỆU THÔNG MINH BẰNG AI
// ==========================================

let tempAiImportData = null; // Lưu trữ tạm thời dữ liệu AI bóc tách được

// Hàm kích hoạt đọc tệp tin thô và gửi lên AI
async function importWithAi(e) {
  if (typeof XLSX === "undefined") {
    alert("Thư viện SheetJS chưa được tải thành công. Vui lòng kiểm tra lại kết nối mạng!");
    return;
  }

  const file = e.target.files[0];
  if (!file) return;

  const fileExt = file.name.split('.').pop().toLowerCase();
  
  // Hiển thị modal loading của AI
  document.getElementById("modalAiAnalysisTitle").innerHTML = `<i class="fa-solid fa-wand-magic-sparkles text-primary"></i> AI đang phân tích dữ liệu tệp tin...`;
  document.getElementById("modalAiAnalysisBody").innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 48px 0; gap: 16px;">
      <div class="table-empty-icon" style="font-size: 3rem; animation: pulse 1.5s infinite; color: #8b5cf6;"><i class="fa-solid fa-wand-magic-sparkles"></i></div>
      <div style="font-weight: 600;" id="aiLoadingText">AI Gemini đang đọc tệp tin thô...</div>
      <div style="font-size: 0.8rem; color: var(--text-muted);">Đang phân tích cấu trúc bảng biểu và chuyển dịch ngữ nghĩa văn bản...</div>
    </div>
  `;
  openModal("modalAiAnalysis");

  const reader = new FileReader();

  if (fileExt === 'xlsx' || fileExt === 'xls') {
    // Nếu là file Excel, đọc nhị phân và biến thành văn bản
    reader.onload = async function(event) {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        let textContent = "";

        workbook.SheetNames.forEach(sheetName => {
          const sheet = workbook.Sheets[sheetName];
          // Chuyển sheet thành dạng văn bản thô CSV để tiết kiệm token và giữ cấu trúc cột
          const csv = XLSX.utils.sheet_to_csv(sheet);
          if (csv.trim()) {
            textContent += `--- SHEET: ${sheetName} ---\n${csv}\n\n`;
          }
        });

        if (!textContent.trim()) {
          throw new Error("Tệp Excel trống hoặc không đọc được dữ liệu bảng biểu.");
        }

        await sendRawDataToGemini(textContent);
      } catch (err) {
        closeModal("modalAiAnalysis");
        alert("Lỗi phân tích file Excel thô: " + err.message);
      }
    };
    reader.readAsArrayBuffer(file);
  } else {
    // Nếu là file văn bản thô (TXT, CSV, JSON)
    reader.onload = async function(event) {
      try {
        const textContent = event.target.result;
        if (!textContent.trim()) {
          throw new Error("Nội dung tệp tin văn bản trống.");
        }
        await sendRawDataToGemini(textContent);
      } catch (err) {
        closeModal("modalAiAnalysis");
        alert("Lỗi đọc tệp tin văn bản: " + err.message);
      }
    };
    reader.readAsText(file);
  }
}

// Gửi dữ liệu văn bản thô lên Gemini bóc tách
async function sendRawDataToGemini(rawDataText) {
  document.getElementById("aiLoadingText").textContent = "AI Gemini đang bóc tách và phân tích ngữ nghĩa...";
  
  const systemSampleSchema = {
    master: [
      { tt: 1, maBsc: "CT-01", goiThauPl: "Xây dựng", nhomCt: "Nhà xưởng", hangMuc: "Ép cọc móng", phuTrach: "Nguyễn Văn A", ngayBdYc: "2026-01-01", ngayKtYc: "2026-03-30", nganSach: 15.5, khHstktc: "", ttHstktc: "Chưa duyệt", ttSpecs: "Đã duyệt", ttBoq: "Đã duyệt", khLcnt: "", ttLcnt: "Chưa duyệt", khHdcu: "", ttHdcu: "Đã ký", khPdKhcu: "", ttKhcu: "Đã duyệt", giaTriHdcu: 15.0, khPlhdCdt: "", ttPlhdCdt: "Chưa ký", khPdKhtk: "", ttKhtk: "Đã duyệt", dk1: "Đạt", dk2: "Đạt", dk3: "Đạt", ngayBdKhoiCong: "2026-01-10", buTienDo: "Bình thường", t1Kh: "Tiến độ 100%", t1Kq: "100%", t1Dg: "Hoàn thành" }
    ],
    so01: [
      { stt: 1, maBsc: "CT-01", hangMuc: "Ép cọc móng", loaiHoSo: "Pháp lý", tenSpham: "Quyết định phê duyệt thiết kế", linkLuuTru: "http://...", ngayHt: "2026-01-05", nguoiLap: "Trần Văn B", nguoiDuyet: "Nguyễn Văn A", ttDuyet: "Đã duyệt" }
    ],
    so02: [
      { stt: 1, maBsc: "CT-01", hangMuc: "Ép cọc móng", thang: "Tháng 01", loaiTaiLieu: "Kế hoạch tuần", noiDungChinh: "Thi công cọc đại trà", datYckt: "Đạt", linkTaiLieu: "", ttLap: "Đã lập", ttDuyet: "Đã duyệt", nguoiLap: "Trần Văn B", nguoiDuyet: "Nguyễn Văn A", ngayDuyet: "2026-01-02" }
    ],
    so03: [
      { maPs: "PS-01", maBsc: "CT-01", hangMuc: "Ép cọc móng", ngayPs: "2026-02-10", loai: "Tăng", moTa: "Phát sinh thêm cọc", nguyenNhan: "Địa chất yếu", deXuat: "Đóng thêm cọc ép", giaTri: 1.2, anhHuongTd: 3, linkHoSo: "", ttDuyet: "Đã duyệt", nguoiDuyet: "Nguyễn Văn A", ngayDuyet: "2026-02-12", noiDungDieuChinh: "" }
    ],
    so04: [
      { maYc: "YC-01", maBsc: "CT-01", hangMuc: "Ép cọc móng", ngayYc: "2026-01-15", loaiYc: "Thiết bị", vatTu: "Máy ép cọc robot", dacTa: "Robot ép cọc 500 tons", kl: 1, dvt: "Bộ", giaTri: 0.5, trongNgoaiHd: "Trong HĐ", linkHoSo: "", ttDuyet: "Đã duyệt", ngayCan: "2026-01-18", ttCungUng: "Đã cung ứng" }
    ],
    so05: [
      { stt: 1, maBsc: "CT-01", hangMuc: "Ép cọc móng", ngayPhatHien: "2026-02-20", mucCham: 5, nguyenNhan: "Mưa bão lớn", giaiPhapBu: "Tăng ca thi công đêm", chiTietGiaiPhap: "Bố trí 2 kíp thi công", mocCamKet: "2026-02-28", linkPhuongAn: "", ttDuyet: "Đã duyệt", kqThucHienBu: "Bắt kịp kế hoạch", ttThucHien: "Đã hoàn thành" }
    ]
  };

  const promptText = `
Bạn là một AI bóc tách dữ liệu thông minh (AI Data Extraction Expert) chuyên nghiệp cho hệ thống ERP xây dựng.
Nhiệm vụ của bạn là đọc kỹ đoạn dữ liệu văn bản thô/bảng biểu Excel thô được tải lên dưới đây, thực hiện bóc tách, chuẩn hóa thông tin và điền dữ liệu vào cấu trúc cơ sở dữ liệu của chúng tôi dưới dạng JSON.

[DỮ LIỆU THÔ ĐƯỢC TẢI LÊN]
${rawDataText}

[YÊU CẦU CẤU TRÚC JSON MẪU ĐẦU RA]
Bạn phải phân bổ các dữ liệu bóc tách được vào 6 mảng tương ứng với schema sau:
${JSON.stringify(systemSampleSchema, null, 2)}

[QUY TẮC BÓC TÁCH NGHIÊM NGẶT]:
1. Phân tích ngữ nghĩa để điền đúng các trường. Nếu dữ liệu thô thiếu trường nào hoặc không thể suy luận được, hãy để trống hoặc đặt giá trị mặc định thích hợp.
2. ÉP KIỂU DỮ LIỆU CHUẨN: Các trường như "nganSach", "giaTriHdcu", "giaTri", "kl" phải là kiểu SỐ THỰC (number). Các trường STT, TT, mucCham, anhHuongTd phải là kiểu SỐ NGUYÊN (integer).
3. ĐỊNH DẠNG NGÀY THÁNG: Các trường ngày tháng phải chuyển đổi về định dạng chuẩn "YYYY-MM-DD" nếu có thông tin ngày tháng trong dữ liệu thô.
4. MÃ BSC LIÊN KẾT: Tự động phát hiện hoặc tự tạo ra Mã BSC định danh (ví dụ: CT-01, CT-02,...) cho mỗi gói thầu. Hãy đảm bảo các bản ghi của 5 Sổ nghiệp vụ phụ có liên quan đến gói thầu nào thì phải được gán CHUNG "maBsc" của gói thầu đó để đảm bảo tính liên kết dữ liệu.
5. CHỈ TRẢ VỀ CHUỖI JSON ĐÚNG CẤU TRÚC. KHÔNG viết thêm bất kỳ văn bản giải thích nào ở đầu hay cuối câu trả lời. KHÔNG bao bọc kết quả trong khối mã markdown (như \`\`\`json ... \`\`\`). Trả về JSON thuần để ứng dụng parse trực tiếp.
  `;

  try {
    const jsonResponse = await callGeminiApi(promptText, { isJsonMode: true, temperature: 0.1 });
    
    // Tách bỏ markdown block nếu AI vẫn trả về dạng ```json ... ```
    let cleanJson = jsonResponse.trim();
    if (cleanJson.startsWith("```")) {
      cleanJson = cleanJson.replace(/^```json/, "").replace(/^```/, "").replace(/```$/, "").trim();
    }

    const parsedData = JSON.parse(cleanJson);

    // Validate dữ liệu tối thiểu
    if (parsedData && (parsedData.master || parsedData.so01 || parsedData.so02 || parsedData.so03 || parsedData.so04 || parsedData.so05)) {
      tempAiImportData = {
        master: parsedData.master || [],
        so01: parsedData.so01 || [],
        so02: parsedData.so02 || [],
        so03: parsedData.so03 || [],
        so04: parsedData.so04 || [],
        so05: parsedData.so05 || []
      };

      closeModal("modalAiAnalysis");

      // Cập nhật thông tin Modal popup options và hiển thị
      const infoMsg = `AI đã bóc tách thành công: 
        <strong>${tempAiImportData.master.length}</strong> Gói thầu Master, 
        <strong>${tempAiImportData.so01.length}</strong> Hồ sơ, 
        <strong>${tempAiImportData.so02.length}</strong> Kế hoạch, 
        <strong>${tempAiImportData.so03.length}</strong> Phát sinh, 
        <strong>${tempAiImportData.so04.length}</strong> Cung ứng, 
        <strong>${tempAiImportData.so05.length}</strong> Lịch trình bù tiến độ.`;
      
      document.getElementById("aiImportMsg").innerHTML = infoMsg;
      openModal("modalAiImportOption");
    } else {
      throw new Error("Dữ liệu bóc tách từ AI không chứa cấu trúc bảng biểu hợp lệ.");
    }
  } catch (err) {
    closeModal("modalAiAnalysis");
    alert("AI không thể bóc tách dữ liệu tệp tin này hoặc trả về JSON lỗi: " + err.message);
    console.error(err);
  }
}

// Áp dụng dữ liệu AI bóc tách được (Ghi đè hoặc Bổ sung)
function applyAiImportData(isOverwrite) {
  if (!tempAiImportData) return;

  if (isOverwrite) {
    // 1. GHI ĐÈ dữ liệu cũ
    state = tempAiImportData;
    alert("Đã ghi đè toàn bộ dữ liệu hệ thống bằng dữ liệu bóc tách của AI!");
  } else {
    // 2. BỔ SUNG dữ liệu tiếp nối
    // Lấy số thứ tự lớn nhất hiện tại để tiếp nối
    let maxMasterTt = state.master.reduce((max, r) => r.tt > max ? r.tt : max, 0);
    
    // Gộp Master
    tempAiImportData.master.forEach(r => {
      // Tránh trùng Mã BSC
      const dup = state.master.find(m => m.maBsc === r.maBsc);
      if (dup) {
        r.maBsc = r.maBsc + "-NEW";
      }
      maxMasterTt++;
      r.tt = maxMasterTt;
      state.master.push(r);
    });

    // Gộp Sổ 01
    let maxSo01Stt = state.so01.reduce((max, r) => r.stt > max ? r.stt : max, 0);
    tempAiImportData.so01.forEach(r => {
      maxSo01Stt++;
      r.stt = maxSo01Stt;
      state.so01.push(r);
    });

    // Gộp Sổ 02
    let maxSo02Stt = state.so02.reduce((max, r) => r.stt > max ? r.stt : max, 0);
    tempAiImportData.so02.forEach(r => {
      maxSo02Stt++;
      r.stt = maxSo02Stt;
      state.so02.push(r);
    });

    // Gộp Sổ 03
    tempAiImportData.so03.forEach(r => {
      const dup = state.so03.find(e => e.maPs === r.maPs);
      if (dup) {
        r.maPs = r.maPs + "-NEW";
      }
      state.so03.push(r);
    });

    // Gộp Sổ 04
    tempAiImportData.so04.forEach(r => {
      const dup = state.so04.find(s => s.maYc === r.maYc);
      if (dup) {
        r.maYc = r.maYc + "-NEW";
      }
      state.so04.push(r);
    });

    // Gộp Sổ 05
    let maxSo05Stt = state.so05.reduce((max, r) => r.stt > max ? r.stt : max, 0);
    tempAiImportData.so05.forEach(r => {
      maxSo05Stt++;
      r.stt = maxSo05Stt;
      state.so05.push(r);
    });

    alert("Đã bổ sung dữ liệu bóc tách của AI vào hệ thống thành công!");
  }

  // Chạy lại công thức tính toán và lưu state
  recalculateAllFormulas();
  saveStateToStorage(true);
  
  // Reset biến tạm và đóng modal
  tempAiImportData = null;
  closeModal("modalAiImportOption");
  
  // Chuyển về Dashboard để xem dữ liệu
  switchTab("dashboard");
}

// ==================== CÁC HÀM XỬ LÝ SUB-TABS & VIEW LEVEL CHO BẢNG MASTER ====================
// Định nghĩa các cột hiển thị cho từng Sub-tab (chỉ số cột từ 0 đến 42)
const MASTER_SUBTAB_COLUMNS = {
  all: Array.from({length: 43}, (_, i) => i),
  cdt: [0, 1, 2, 3, 4, 5, 17, 18, 42], // A. Đầu vào CĐT
  contract: [0, 1, 2, 3, 4, 5, 6, 7, 19, 20, 21, 42], // B. Cung ứng & Hợp đồng
  plan: [0, 1, 2, 3, 4, 14, 15, 16, 22, 27, 42], // C. Kế hoạch triển khai
  start: [0, 1, 2, 3, 4, 8, 9, 23, 24, 25, 26, 42], // D. Chốt chặn khởi công
  budget: [0, 1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 28, 29, 42], // E. Ngân sách & Chi phí
  exec: [0, 1, 2, 3, 4, 13, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42] // G. Quản lý thi công
};

// Các cột ẩn ở "Cấp công trình"
const PROJECT_LEVEL_HIDDEN_COLUMNS = [
  23, 24, 25, // ĐK1, ĐK2, ĐK3
  30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41 // Các tuần thi công T1-T4
];

window.setMasterViewLevel = function(level) {
  currentMasterViewLevel = level;
  
  // Cập nhật giao diện nút
  const btnProject = document.getElementById("viewLevelProjectBtn");
  const btnDetail = document.getElementById("viewLevelDetailBtn");
  if (btnProject && btnDetail) {
    btnProject.classList.toggle("active", level === "project");
    btnDetail.classList.toggle("active", level === "detail");
  }
  
  renderMasterTable();
  applyMasterColumnVisibility();
};

window.toggleLevel1JS = function(parentTt) {
  const rows = document.querySelectorAll("#masterTableBody tr");
  const btn = document.getElementById(`btn-toggle-${parentTt.replace(/\./g, '_')}-cdt`);
  if (!rows || rows.length === 0) return;
  
  let isHidden = false;
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const tt = row.getAttribute("data-tt");
    if (tt && tt !== parentTt && tt.startsWith(parentTt + ".")) {
      isHidden = (row.style.display === 'none' || window.getComputedStyle(row).display === 'none');
      break;
    }
  }
  
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const tt = row.getAttribute("data-tt");
    if (tt && tt !== parentTt && tt.startsWith(parentTt + ".")) {
      row.style.display = isHidden ? "" : "none";
    }
  }
  
  if (btn) {
    btn.innerHTML = isHidden ? "—" : "+";
  }
};

window.toggleLevel2JS = function(parentTt) {
  const rows = document.querySelectorAll("#masterTableBody tr");
  const btn = document.getElementById(`btn-toggle-${parentTt.replace(/\./g, '_')}-cdt`);
  if (!rows || rows.length === 0) return;
  
  let isHidden = false;
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const tt = row.getAttribute("data-tt");
    if (tt && tt !== parentTt && tt.startsWith(parentTt + ".")) {
      isHidden = (row.style.display === 'none' || window.getComputedStyle(row).display === 'none');
      break;
    }
  }
  
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const tt = row.getAttribute("data-tt");
    if (tt && tt !== parentTt && tt.startsWith(parentTt + ".")) {
      row.style.display = isHidden ? "" : "none";
    }
  }
  
  if (btn) {
    btn.innerHTML = isHidden ? "—" : "+";
  }
};

// Bí danh để tương thích ngược nếu có
window.togglePackageJS = window.toggleLevel1JS;

window.setMasterSubTab = function(subtab) {
  currentMasterSubTab = subtab;
  
  // Cập nhật class active trên nút Sub-tabs
  const subtabs = ["all", "cdt", "contract", "plan", "start", "budget", "exec"];
  subtabs.forEach(tab => {
    const btn = document.getElementById(`subtab${tab.charAt(0).toUpperCase() + tab.slice(1)}Btn`);
    if (btn) {
      btn.classList.toggle("active", tab === subtab);
    }
  });
  
  applyMasterColumnVisibility();
};

window.applyMasterColumnVisibility = function() {
  const table = document.getElementById("masterDataTable");
  if (!table) return;
  
  const activeCols = MASTER_SUBTAB_COLUMNS[currentMasterSubTab] || MASTER_SUBTAB_COLUMNS.all;
  const theadRows = table.querySelectorAll("thead tr");
  const tbodyRows = table.querySelectorAll("tbody tr");
  
  // 1. Xử lý Header
  theadRows.forEach(row => {
    const ths = row.querySelectorAll("th");
    ths.forEach((th, idx) => {
      let shouldShow = activeCols.includes(idx);
      if (shouldShow && currentMasterViewLevel === "project") {
        if (PROJECT_LEVEL_HIDDEN_COLUMNS.includes(idx)) {
          shouldShow = false;
        }
      }
      th.style.display = shouldShow ? "" : "none";
    });
  });
  
  // 2. Xử lý Body
  tbodyRows.forEach(row => {
    const tds = row.querySelectorAll("td");
    tds.forEach((td, idx) => {
      if (idx >= tds.length) return;
      let shouldShow = activeCols.includes(idx);
      if (shouldShow && currentMasterViewLevel === "project") {
        if (PROJECT_LEVEL_HIDDEN_COLUMNS.includes(idx)) {
          shouldShow = false;
        }
      }
      td.style.display = shouldShow ? "" : "none";
    });
  });
};
