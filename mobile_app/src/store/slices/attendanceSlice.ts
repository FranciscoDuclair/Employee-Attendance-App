import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface AttendanceRecord {
  id: number;
  date: string;
  check_in_time: string | null;
  check_out_time: string | null;
  status: string;
  hours_worked: number;
}

interface AttendanceState {
  records: AttendanceRecord[];
  todayRecord: AttendanceRecord | null;
  isLoading: boolean;
  error: string | null;
}

const initialState: AttendanceState = {
  records: [],
  todayRecord: null,
  isLoading: false,
  error: null,
};

const attendanceSlice = createSlice({
  name: 'attendance',
  initialState,
  reducers: {
    setLoading: (state, action: PayloadAction<boolean>) => {
      state.isLoading = action.payload;
    },
    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
    },
    setRecords: (state, action: PayloadAction<AttendanceRecord[]>) => {
      state.records = action.payload;
    },
    setTodayRecord: (state, action: PayloadAction<AttendanceRecord | null>) => {
      state.todayRecord = action.payload;
    },
    addRecord: (state, action: PayloadAction<AttendanceRecord>) => {
      state.records.unshift(action.payload);
    },
    updateRecord: (state, action: PayloadAction<AttendanceRecord>) => {
      const index = state.records.findIndex(record => record.id === action.payload.id);
      if (index !== -1) {
        state.records[index] = action.payload;
      }
      if (state.todayRecord?.id === action.payload.id) {
        state.todayRecord = action.payload;
      }
    },
  },
});

export const { 
  setLoading, 
  setError, 
  setRecords, 
  setTodayRecord, 
  addRecord, 
  updateRecord 
} = attendanceSlice.actions;
export default attendanceSlice.reducer;
